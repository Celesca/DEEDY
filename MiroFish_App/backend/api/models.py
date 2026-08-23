from pydantic import BaseModel, Field
from typing import Optional, Dict

class CampaignInput(BaseModel):
    objective: str = Field(..., description="Campaign Objective")
    brand_voice: str = Field(..., description="Brand Voice")
    company_description: str = Field(..., description="Description of the company or brand")
    post_content: str = Field(..., description="The caption or text of the post")
    platforms: list[str] = Field(["X"], description="Target platforms (e.g., X, Facebook)")
    agent_count: int = Field(1000, description="Number of agents to simulate")
    demographics: Dict[str, int] = Field(..., description="Mix of demographics")
    pre_bias: str = Field("Neutral", description="Starting sentiment bias")
    target_demographics: Optional[list[str]] = Field(None, description="E.g., ['Gen Z', 'Gen Y']")
    use_kol: bool = Field(False, description="Whether to inject content directly to KOLs first")
    io_mode: str = Field("None", description="Astroturfing mode: None, Positive IO, Negative IO")
