from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LocationPayload:
    name: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "LocationPayload | None":
        if not payload:
            return None
        return cls(
            name=payload.get("name"),
            city=payload.get("city"),
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


@dataclass(slots=True)
class TranscodeJob:
    upload_id: str
    user_id: str
    s3_input_key: str
    description: str = ""
    hashtags: list[str] = field(default_factory=list)
    location: LocationPayload | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TranscodeJob":
        return cls(
            upload_id=payload["upload_id"],
            user_id=payload["user_id"],
            s3_input_key=payload["s3_input_key"],
            description=payload.get("description", ""),
            hashtags=list(payload.get("hashtags", [])),
            location=LocationPayload.from_dict(payload.get("location")),
        )
