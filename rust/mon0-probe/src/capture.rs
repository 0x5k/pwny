use crate::parser::parse_ap;
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    ffi::CString,
    fs::{self, File},
    io::{self, Write},
    mem,
    os::fd::{AsRawFd, FromRawFd, OwnedFd},
    path::Path,
    process::Command,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub fn run() -> io::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let iface = args.get(1).map(String::as_str).unwrap_or("mon0");
    let seconds: u64 = args
        .get(2)
        .map(String::as_str)
        .unwrap_or("30")
        .parse()
        .map_err(|_| {
            io::Error::new(
                io::ErrorKind::InvalidInput,
                "duration must be seconds; 0 means continuous",
            )
        })?;
    let output = args
        .get(3)
        .map(String::as_str)
        .unwrap_or("/run/pwnagotchi/recon.json");
    let parent = Path::new(output).parent().unwrap_or(Path::new("."));
    fs::create_dir_all(parent)?;
    let lock = File::create(parent.join("recon.lock"))?;
    if unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } < 0 {
        return Err(io::Error::last_os_error());
    }
    let name = CString::new(iface)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "interface contains NUL"))?;
    let index = unsafe { libc::if_nametoindex(name.as_ptr()) };
    if index == 0 {
        return Err(io::Error::last_os_error());
    }
    let fd = unsafe {
        libc::socket(
            libc::AF_PACKET,
            libc::SOCK_RAW | libc::SOCK_CLOEXEC | libc::SOCK_NONBLOCK,
            (libc::ETH_P_ALL as u16).to_be() as i32,
        )
    };
    if fd < 0 {
        return Err(io::Error::last_os_error());
    }
    let fd = unsafe { OwnedFd::from_raw_fd(fd) };
    let mut address: libc::sockaddr_ll = unsafe { mem::zeroed() };
    address.sll_family = libc::AF_PACKET as u16;
    address.sll_protocol = (libc::ETH_P_ALL as u16).to_be();
    address.sll_ifindex = index as i32;
    if unsafe {
        libc::bind(
            fd.as_raw_fd(),
            &address as *const _ as *const libc::sockaddr,
            mem::size_of_val(&address) as libc::socklen_t,
        )
    } < 0
    {
        return Err(io::Error::last_os_error());
    }
    if fs::read_to_string(format!("/sys/class/net/{iface}/type"))?.trim() != "803" {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "interface must expose radiotap (ARPHRD 803)",
        ));
    }
    let started = Instant::now();
    let mut hop = Instant::now();
    let mut publish = Instant::now();
    let channels = [1u8, 6, 11];
    let mut next = 0;
    let mut current = None;
    let mut hops = 0u64;
    let mut errors = 0u64;
    let mut last_error = String::new();
    let mut frames = 0u64;
    let mut aps: BTreeMap<String, Value> = BTreeMap::new();
    let mut buf = [0u8; 65536];
    let mut capture = new_pcap(&parent.join("capture.pcap"))?;
    let mut capture_bytes = 24usize;
    loop {
        if Instant::now() >= hop {
            let channel = channels[next];
            next = (next + 1) % channels.len();
            let result = Command::new("/usr/sbin/iw")
                .args(["dev", iface, "set", "channel", &channel.to_string()])
                .output()?;
            if result.status.success() {
                current = Some(channel);
                hops += 1;
                last_error.clear();
            } else {
                errors += 1;
                last_error = String::from_utf8_lossy(&result.stderr).trim().to_string();
                eprintln!("channel {channel}: {last_error}");
            }
            hop = Instant::now() + Duration::from_secs(2);
        }
        let n = unsafe { libc::recv(fd.as_raw_fd(), buf.as_mut_ptr().cast(), buf.len(), 0) };
        if n < 0 {
            let error = io::Error::last_os_error();
            if !matches!(
                error.kind(),
                io::ErrorKind::WouldBlock | io::ErrorKind::Interrupted
            ) {
                return Err(error);
            }
            std::thread::sleep(Duration::from_millis(5));
        } else {
            let packet = &buf[..n as usize];
            frames += 1;
            if capture_bytes + packet.len() + 16 > 8 * 1024 * 1024 {
                capture.flush()?;
                fs::rename(
                    parent.join("capture.pcap"),
                    parent.join("capture.previous.pcap"),
                )?;
                capture = new_pcap(&parent.join("capture.pcap"))?;
                capture_bytes = 24;
            }
            let stamp = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default();
            for v in [
                stamp.as_secs() as u32,
                stamp.subsec_micros(),
                packet.len() as u32,
                packet.len() as u32,
            ] {
                capture.write_all(&v.to_le_bytes())?;
            }
            capture.write_all(packet)?;
            capture_bytes += packet.len() + 16;
            if let Some(mut ap) = parse_ap(packet) {
                ap["last_seen"] = json!(now());
                let key = ap["mac"].as_str().unwrap().to_string();
                if ap["ssid"] == "" {
                    if let Some(old) = aps.get(&key) {
                        ap["ssid"] = old["ssid"].clone();
                        ap["hostname"] = old["hostname"].clone();
                    }
                }
                if aps.len() < 4096 || aps.contains_key(&key) {
                    aps.insert(key, ap);
                }
            }
        }
        let finished = seconds > 0 && started.elapsed() >= Duration::from_secs(seconds);
        if Instant::now() >= publish || finished {
            aps.retain(|_, ap| now().saturating_sub(ap["last_seen"].as_u64().unwrap_or(0)) <= 120);
            let snapshot = json!({"version":1,"source":"rust","updated_at":now(),"interface":iface,
                "current_channel":current,"frames":frames,"successful_hops":hops,"hop_errors":errors,
                "last_hop_error":last_error,"aps":aps.values().collect::<Vec<_>>()});
            let temp = format!("{output}.tmp");
            fs::write(&temp, serde_json::to_vec(&snapshot)?)?;
            fs::rename(temp, output)?;
            capture.flush()?;
            publish = Instant::now() + Duration::from_secs(1);
        }
        if finished {
            return Ok(());
        }
    }
}
fn new_pcap(path: &Path) -> io::Result<File> {
    let mut file = File::create(path)?;
    file.write_all(&0xa1b2c3d4u32.to_le_bytes())?;
    file.write_all(&2u16.to_le_bytes())?;
    file.write_all(&4u16.to_le_bytes())?;
    for v in [0u32, 0, 65536, 127] {
        file.write_all(&v.to_le_bytes())?;
    }
    Ok(file)
}
