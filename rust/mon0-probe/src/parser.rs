use serde_json::{json, Value};

// Beacon/probe-response IEs follow 24 MAC-header bytes and 12 fixed bytes.
pub fn parse_ap(packet: &[u8]) -> Option<Value> {
    if packet.len() < 8 || packet[0] != 0 {
        return None;
    }
    let rt = u16::from_le_bytes([packet[2], packet[3]]) as usize;
    if rt < 8 {
        return None;
    }
    let header = packet.get(..rt)?;
    let present = u32::from_le_bytes(header[4..8].try_into().ok()?);
    let mut fields = 8usize;
    let mut bitmap = present;
    while bitmap & (1 << 31) != 0 {
        bitmap = u32::from_le_bytes(header.get(fields..fields + 4)?.try_into().ok()?);
        fields += 4;
    }
    if present & 1 != 0 {
        fields = (fields + 7) & !7;
        fields += 8; // TSFT precedes the flags field and is aligned to eight bytes.
    }
    let flags = if present & 2 != 0 {
        *header.get(fields)?
    } else {
        0
    };
    if flags & 0x40 != 0 {
        return None;
    } // Driver marked the frame's FCS invalid.
    let mut frame = packet.get(rt..)?;
    if flags & 0x10 != 0 {
        frame = frame.get(..frame.len().checked_sub(4)?)?;
    }
    if frame.len() < 36 || !matches!(frame[0], 0x80 | 0x50) {
        return None;
    }
    let mac = frame[16..22]
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<Vec<_>>()
        .join(":");
    let private = frame[34] & 0x10 != 0;
    let mut ssid = None;
    let mut channel = None;
    let mut rsn = false;
    let mut wpa = false;
    let mut ies = &frame[36..];
    while !ies.is_empty() {
        if ies.len() < 2 {
            return None;
        }
        let len = ies[1] as usize;
        let data = ies.get(2..2 + len)?;
        match ies[0] {
            0 if len <= 32 => ssid = Some(String::from_utf8_lossy(data).into_owned()),
            3 if len == 1 => channel = Some(data[0]),
            61 if len >= 1 && channel.is_none() => channel = Some(data[0]),
            48 => rsn = true,
            221 if data.starts_with(&[0x00, 0x50, 0xf2, 1]) => wpa = true,
            _ => {}
        }
        ies = &ies[2 + len..];
    }
    let ssid = ssid?;
    Some(
        json!({"mac":mac,"hostname":ssid,"ssid":ssid,"channel":channel,
        "encryption":if rsn {"RSN"} else if wpa {"WPA"} else if private {"WEP"} else {"OPEN"},
        "clients":[],"vendor":"","rssi":null}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn beacon() -> Vec<u8> {
        let mut p = vec![0; 44];
        p[2] = 8;
        p[8] = 0x80;
        p[24..30].copy_from_slice(&[1, 2, 3, 4, 5, 6]);
        p.extend_from_slice(&[0, 4, b't', b'e', b's', b't', 3, 1, 6, 48, 2, 1, 0]);
        p
    }
    #[test]
    fn fixed_fields_and_bssid() {
        let ap = parse_ap(&beacon()).unwrap();
        assert_eq!(ap["ssid"], "test");
        assert_eq!(ap["mac"], "01:02:03:04:05:06");
        assert_eq!(ap["channel"], 6);
        assert_eq!(ap["encryption"], "RSN");
    }
    #[test]
    fn truncated_and_data_rejected() {
        let p = beacon();
        for n in 0..44 {
            assert!(parse_ap(&p[..n]).is_none());
        }
        let mut p = p;
        p[8] = 0x88;
        assert!(parse_ap(&p).is_none());
    }
    #[test]
    fn malformed_ie_rejected() {
        let mut p = beacon();
        p.extend_from_slice(&[0, 32, 1]);
        assert!(parse_ap(&p).is_none());
    }
    #[test]
    fn radiotap_fcs_and_bad_fcs() {
        let original = beacon();
        let mut p = vec![0, 0, 9, 0, 2, 0, 0, 0, 0x10];
        p.extend_from_slice(&original[8..]);
        p.extend_from_slice(&[0xff, 0xff, 0xff, 0xff]);
        assert_eq!(parse_ap(&p).unwrap()["ssid"], "test");
        p[8] |= 0x40;
        assert!(parse_ap(&p).is_none());
    }
}
