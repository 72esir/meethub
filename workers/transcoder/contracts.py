from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TranscodeJob:
    upload_id: str
    user_id: str
    s3_input_key: str
    description: str = ""
    hashtags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TranscodeJob":
        return cls(
            upload_id=payload["upload_id"],
            user_id=payload["user_id"],
            s3_input_key=payload["s3_input_key"],
            description=payload.get("description", ""),
            hashtags=list(payload.get("hashtags", [])),
        )
