from dataclasses import dataclass, field


@dataclass
class AfishaEvent:
    """Одно мероприятие с Яндекс.Афиши."""

    external_id: str
    title: str
    description: str
    city: str
    place_name: str | None
    latitude: float | None
    longitude: float | None
    image_url: str | None
    tags: list[str] = field(default_factory=list)
