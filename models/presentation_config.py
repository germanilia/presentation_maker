from typing import List, Union, Optional, Literal
from pydantic import BaseModel, Field

from models.slide import PowerPointSlide

class Color(BaseModel):
    r: int
    g: int
    b: int

class TableColors(BaseModel):
    header: Color
    text: Color

class ThemeColors(BaseModel):
    title: Color
    text: Color
    bullet: Color
    table: TableColors
    footer: Color

class Font(BaseModel):
    name: str
    size: int

class ThemeFonts(BaseModel):
    title: Font
    text: Font
    table: Font
    footer: Font

class Theme(BaseModel):
    colors: ThemeColors
    fonts: ThemeFonts
    footer: str

class BulletPoint(BaseModel):
    text: str
    level: Optional[int] = Field(default=0, ge=0)

class TableContent(BaseModel):
    headers: List[str]
    rows: List[List[str]]

class Slide(BaseModel):
    title: str
    subtitle: Optional[str] = None
    style: Literal["cover", "bullets", "table", "paragraph"]
    content: Optional[Union[str, List[Union[str, BulletPoint]], TableContent]] = None
    image_path: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Example Slide",
                    "subtitle": "Optional Subtitle",
                    "style": "bullets",
                    "content": [
                        "Simple bullet point",
                        {"text": "Nested bullet point", "level": 1}
                    ]
                }
            ]
        }
    }

class PresentationConfig(BaseModel):
    theme: Theme
    topic: str
    general_instructions: str
    sub_topics: List[str]
    number_of_slides: int
    logo_base64: str = ""
    logo_path: str = ""
    logo_description: str = ""
    output_path: str
    search_source: Literal["youtube", "serper"] = "serper"
    slides: Optional[List[PowerPointSlide]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "theme": {
                    "colors": {
                        "title": {"r": 102, "g": 45, "b": 145},
                        # ... other color examples
                    },
                    "fonts": {
                        "title": {"name": "Arial", "size": 32},
                        # ... other font examples
                    },
                    "footer": "Cellcom - Churn Prediction POC"
                },
                "topic": "open ai recent announcements",
                "general_instructions": "Create a detailed summary...",
                "number_of_slides": 7,
                "output_path": "presentation.pptx"
            }]
        }
    } 