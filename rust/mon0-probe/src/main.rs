#[cfg(target_os = "linux")]
mod capture;
mod parser;

fn main() -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    return capture::run();
    #[cfg(not(target_os = "linux"))]
    Err(std::io::Error::new(
        std::io::ErrorKind::Unsupported,
        "capture requires Linux",
    ))
}
