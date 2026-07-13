use flate2::read::ZlibDecoder;
use flate2::write::ZlibEncoder;
use flate2::Compression;
use std::io::{Read, Write};
use thiserror::Error;

pub const KEYFRAME_INTERVAL: u32 = 48;
pub const CELL_BYTES: usize = 4;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum CodecTag {
    Raw = 0,
    Zlib = 1,
    Delta = 2,
    RleFull = 3,
}

impl CodecTag {
    fn from_byte(value: u8) -> Result<Self, CodecError> {
        match value {
            0 => Ok(Self::Raw),
            1 => Ok(Self::Zlib),
            2 => Ok(Self::Delta),
            3 => Ok(Self::RleFull),
            tag => Err(CodecError::UnknownTag(tag)),
        }
    }
}

#[derive(Debug, Error)]
pub enum CodecError {
    #[error("adaptive message too short")]
    MessageTooShort,
    #[error("unknown adaptive codec tag: {0}")]
    UnknownTag(u8),
    #[error("delta frame cannot decode without a previous frame")]
    DeltaWithoutPrevious,
    #[error("frame length {0} is not divisible by cell size {1}")]
    InvalidFrameLength(usize, usize),
    #[error("zlib error: {0}")]
    Zlib(#[from] std::io::Error),
}

#[derive(Clone, Debug)]
pub struct EncodedFrame {
    pub message: Vec<u8>,
    pub shown_frame: Vec<u8>,
    pub tag: CodecTag,
    pub changed_cells: usize,
    pub encoded_size: usize,
    pub raw_size: usize,
    pub is_keyframe: bool,
}

fn zlib_compress(bytes: &[u8], level: u32) -> Result<Vec<u8>, CodecError> {
    let mut encoder = ZlibEncoder::new(Vec::new(), Compression::new(level));
    encoder.write_all(bytes)?;
    Ok(encoder.finish()?)
}

fn zlib_decompress(bytes: &[u8]) -> Result<Vec<u8>, CodecError> {
    let mut decoder = ZlibDecoder::new(bytes);
    let mut out = Vec::new();
    decoder.read_to_end(&mut out)?;
    Ok(out)
}

fn rle_encode(frame: &[u8], cell_bytes: usize) -> Result<Vec<u8>, CodecError> {
    if !frame.len().is_multiple_of(cell_bytes) {
        return Err(CodecError::InvalidFrameLength(frame.len(), cell_bytes));
    }
    if frame.is_empty() {
        return Ok(Vec::new());
    }

    let mut out = Vec::new();
    let mut prev = &frame[0..cell_bytes];
    let mut count: u16 = 0;
    for cell in frame.chunks_exact(cell_bytes) {
        if cell == prev && count < u16::MAX {
            count += 1;
            continue;
        }
        out.extend_from_slice(&count.to_le_bytes());
        out.extend_from_slice(prev);
        prev = cell;
        count = 1;
    }
    out.extend_from_slice(&count.to_le_bytes());
    out.extend_from_slice(prev);
    Ok(out)
}

fn envelope(frame_index: u32, tag: CodecTag, payload: Vec<u8>) -> Vec<u8> {
    let mut message = Vec::with_capacity(5 + payload.len());
    message.extend_from_slice(&frame_index.to_be_bytes());
    message.push(tag as u8);
    message.extend_from_slice(&payload);
    message
}

fn full_frame(
    frame: &[u8],
    frame_index: u32,
    cell_bytes: usize,
    level: u32,
) -> Result<EncodedFrame, CodecError> {
    let z_raw = zlib_compress(frame, level)?;
    let z_rle = zlib_compress(&rle_encode(frame, cell_bytes)?, level)?;

    let (tag, payload) = [
        (CodecTag::Raw, frame.to_vec()),
        (CodecTag::Zlib, z_raw),
        (CodecTag::RleFull, z_rle),
    ]
    .into_iter()
    .min_by_key(|(_, payload)| payload.len())
    .expect("full-frame candidate list is non-empty");
    let message = envelope(frame_index, tag, payload);
    Ok(EncodedFrame {
        encoded_size: message.len(),
        message,
        shown_frame: frame.to_vec(),
        tag,
        changed_cells: frame.len() / cell_bytes,
        raw_size: frame.len(),
        is_keyframe: true,
    })
}

pub fn encode_full_frame(
    frame: &[u8],
    frame_index: u32,
    cell_bytes: usize,
) -> Result<EncodedFrame, CodecError> {
    if !frame.len().is_multiple_of(cell_bytes) {
        return Err(CodecError::InvalidFrameLength(frame.len(), cell_bytes));
    }
    full_frame(frame, frame_index, cell_bytes, 3)
}

pub fn encode_frame(
    frame: &[u8],
    prev: Option<&[u8]>,
    frame_index: u32,
    cell_bytes: usize,
) -> Result<EncodedFrame, CodecError> {
    if !frame.len().is_multiple_of(cell_bytes) {
        return Err(CodecError::InvalidFrameLength(frame.len(), cell_bytes));
    }
    let keyframe = prev.is_none()
        || prev.is_some_and(|prior| prior.len() != frame.len())
        || frame_index.is_multiple_of(KEYFRAME_INTERVAL);
    if keyframe {
        return encode_full_frame(frame, frame_index, cell_bytes);
    }
    let prev = prev.expect("checked above");
    let cell_count = frame.len() / cell_bytes;
    let mut changed_indices = Vec::new();
    let mut changed_values = Vec::new();

    for (cell_index, (current, prior)) in frame
        .chunks_exact(cell_bytes)
        .zip(prev.chunks_exact(cell_bytes))
        .enumerate()
    {
        if current != prior {
            changed_indices.push(cell_index as u32);
            changed_values.extend_from_slice(current);
        }
    }

    let fraction_changed = changed_indices.len() as f32 / cell_count.max(1) as f32;
    let mut candidates: Vec<(CodecTag, Vec<u8>, Vec<u8>)> = Vec::new();

    if fraction_changed < 0.60 {
        let mut body = Vec::with_capacity(changed_indices.len() * (4 + cell_bytes));
        for index in &changed_indices {
            body.extend_from_slice(&index.to_le_bytes());
        }
        body.extend_from_slice(&changed_values);
        let mut shown = prev.to_vec();
        apply_delta_in_place(&mut shown, &changed_indices, &changed_values, cell_bytes);
        candidates.push((CodecTag::Delta, zlib_compress(&body, 3)?, shown));
    }

    if fraction_changed >= 0.10 || candidates.is_empty() {
        let z_raw = zlib_compress(frame, 3)?;
        let z_rle = zlib_compress(&rle_encode(frame, cell_bytes)?, 3)?;
        if z_rle.len() < z_raw.len() {
            candidates.push((CodecTag::RleFull, z_rle, frame.to_vec()));
        } else {
            candidates.push((CodecTag::Zlib, z_raw, frame.to_vec()));
        }
    }

    let (mut tag, mut payload, mut shown) = candidates
        .into_iter()
        .min_by_key(|(_, payload, _)| payload.len())
        .expect("at least one codec candidate");
    if frame.len() < payload.len() {
        tag = CodecTag::Raw;
        payload = frame.to_vec();
        shown = frame.to_vec();
    }

    let message = envelope(frame_index, tag, payload);
    Ok(EncodedFrame {
        encoded_size: message.len(),
        message,
        shown_frame: shown,
        tag,
        changed_cells: changed_indices.len(),
        raw_size: frame.len(),
        is_keyframe: false,
    })
}

fn apply_delta_in_place(frame: &mut [u8], indices: &[u32], values: &[u8], cell_bytes: usize) {
    for (i, index) in indices.iter().enumerate() {
        let dst = *index as usize * cell_bytes;
        let src = i * cell_bytes;
        frame[dst..dst + cell_bytes].copy_from_slice(&values[src..src + cell_bytes]);
    }
}

pub fn decode_frame(
    message: &[u8],
    prev: Option<&[u8]>,
    cell_bytes: usize,
) -> Result<(u32, Vec<u8>, CodecTag), CodecError> {
    if message.len() < 5 {
        return Err(CodecError::MessageTooShort);
    }
    let frame_index = u32::from_be_bytes([message[0], message[1], message[2], message[3]]);
    let tag = CodecTag::from_byte(message[4])?;
    let payload = &message[5..];
    let frame = match tag {
        CodecTag::Raw => payload.to_vec(),
        CodecTag::Zlib => zlib_decompress(payload)?,
        CodecTag::RleFull => {
            let body = zlib_decompress(payload)?;
            let mut out = Vec::new();
            let mut offset = 0;
            while offset + 2 + cell_bytes <= body.len() {
                let count = u16::from_le_bytes([body[offset], body[offset + 1]]) as usize;
                let cell = &body[offset + 2..offset + 2 + cell_bytes];
                for _ in 0..count {
                    out.extend_from_slice(cell);
                }
                offset += 2 + cell_bytes;
            }
            out
        }
        CodecTag::Delta => {
            let prev = prev.ok_or(CodecError::DeltaWithoutPrevious)?;
            let body = zlib_decompress(payload)?;
            let count = body.len() / (4 + cell_bytes);
            let mut indices = Vec::with_capacity(count);
            for i in 0..count {
                let start = i * 4;
                indices.push(u32::from_le_bytes([
                    body[start],
                    body[start + 1],
                    body[start + 2],
                    body[start + 3],
                ]));
            }
            let values_offset = count * 4;
            let values = &body[values_offset..];
            let mut out = prev.to_vec();
            apply_delta_in_place(&mut out, &indices, values, cell_bytes);
            out
        }
    };
    Ok((frame_index, frame, tag))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keyframe_round_trips() {
        let frame = [b'@', 1, 2, 3].repeat(16);
        let encoded = encode_frame(&frame, None, 0, CELL_BYTES).expect("encode");
        let (index, decoded, _) = decode_frame(&encoded.message, None, CELL_BYTES).expect("decode");
        assert_eq!(index, 0);
        assert_eq!(decoded, frame);
        assert!(encoded.is_keyframe);
    }

    #[test]
    fn delta_round_trips() {
        let first = [b' ', 255, 255, 255].repeat(64);
        let mut second = first.clone();
        second[10 * CELL_BYTES] = b'*';
        second[10 * CELL_BYTES + 1] = 38;
        let key = encode_frame(&first, None, 0, CELL_BYTES).expect("key");
        let delta = encode_frame(&second, Some(&key.shown_frame), 1, CELL_BYTES).expect("delta");
        let (index, decoded, _) =
            decode_frame(&delta.message, Some(&key.shown_frame), CELL_BYTES).expect("decode");
        assert_eq!(index, 1);
        assert_eq!(decoded, second);
    }

    #[test]
    fn pure_full_frame_encode_does_not_need_or_mutate_history() {
        let frame = [b'#', 10, 20, 30].repeat(32);
        let before = frame.clone();
        let encoded = encode_full_frame(&frame, 91, CELL_BYTES).expect("full frame");
        let (index, decoded, tag) =
            decode_frame(&encoded.message, None, CELL_BYTES).expect("decode");
        assert_eq!(index, 91);
        assert_eq!(decoded, frame);
        assert_eq!(frame, before);
        assert_ne!(tag, CodecTag::Delta);
    }
}
