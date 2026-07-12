from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class FrameDiagnostics:
    frame_sequence: int = 0
    codec_tag: int = 0
    raw_frame_size: int = 0
    encoded_frame_size: int = 0
    delta_cell_count: int = 0
    keyframe_count: int = 0
    dropped_frame_count: int = 0
    reconnect_count: int = 0
    fps: float = 0.0
    bandwidth_ratio: float = 1.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        data = {
            "frame_sequence": self.frame_sequence,
            "codec_tag": self.codec_tag,
            "raw_frame_size": self.raw_frame_size,
            "encoded_frame_size": self.encoded_frame_size,
            "delta_cell_count": self.delta_cell_count,
            "keyframe_count": self.keyframe_count,
            "dropped_frame_count": self.dropped_frame_count,
            "reconnect_count": self.reconnect_count,
            "fps": self.fps,
            "bandwidth_ratio": self.bandwidth_ratio,
        }
        data.update(self.extra)
        return data
