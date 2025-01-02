from typing import List, Union, Optional
from pydantic import BaseModel

class BulletPoint(BaseModel):
    text: str
    level: Optional[int] = 0

class TableContent(BaseModel):
    headers: List[str]
    rows: List[List[str]]

class PowerPointSlide(BaseModel):
    title: str
    subtitle: str
    style: str
    content: Union[str, List[Union[str, BulletPoint]], TableContent]
    comments: Optional[str]  = None
    image_path: str = ""
    layout: dict = {"image_position": "right", "image_width": 0.5}

    # Validate style values
    def model_post_init(self, __context) -> None:
        valid_styles = {"cover", "bullets", "table", "paragraph"}
        if self.style not in valid_styles:
            raise ValueError(f"Style must be one of {valid_styles}")

class PowerPointSlides(BaseModel):
    slides: List[PowerPointSlide]
