"""Request/response schemas. Generated from data/processed/split_metadata.json.
The 39 model input features are exact; extra fields (Address, FLAG, ...) are forbidden,
so no target label or identifier can influence a prediction."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ORDERED_FEATURES: list[str] = [
    'Avg min between sent tnx',
    'Avg min between received tnx',
    'Time Diff between first and last (Mins)',
    'Sent tnx',
    'Received Tnx',
    'Number of Created Contracts',
    'Unique Received From Addresses',
    'Unique Sent To Addresses',
    'min value received',
    'max value received ',
    'avg val received',
    'min val sent',
    'max val sent',
    'avg val sent',
    'min value sent to contract',
    'max val sent to contract',
    'avg value sent to contract',
    'total transactions (including tnx to create contract',
    'total Ether sent',
    'total ether received',
    'total ether sent contracts',
    'total ether balance',
    ' Total ERC20 tnxs',
    ' ERC20 total Ether received',
    ' ERC20 total ether sent',
    ' ERC20 total Ether sent contract',
    ' ERC20 uniq sent addr',
    ' ERC20 uniq rec addr',
    ' ERC20 uniq rec contract addr',
    ' ERC20 min val rec',
    ' ERC20 max val rec',
    ' ERC20 avg val rec',
    ' ERC20 min val sent',
    ' ERC20 max val sent',
    ' ERC20 avg val sent',
    ' ERC20 uniq sent token name',
    ' ERC20 uniq rec token name',
    ' ERC20 most sent token type',
    ' ERC20_most_rec_token_type',
]

NUMERIC_FIELDS: set[str] = {    'avg_min_between_sent_tnx',
    'avg_min_between_received_tnx',
    'time_diff_between_first_and_last_mins',
    'sent_tnx',
    'received_tnx',
    'number_of_created_contracts',
    'unique_received_from_addresses',
    'unique_sent_to_addresses',
    'min_value_received',
    'max_value_received',
    'avg_val_received',
    'min_val_sent',
    'max_val_sent',
    'avg_val_sent',
    'min_value_sent_to_contract',
    'max_val_sent_to_contract',
    'avg_value_sent_to_contract',
    'total_transactions_including_tnx_to_create_contract',
    'total_ether_sent',
    'total_ether_received',
    'total_ether_sent_contracts',
    'total_ether_balance',
    'total_erc20_tnxs',
    'erc20_total_ether_received',
    'erc20_total_ether_sent',
    'erc20_total_ether_sent_contract',
    'erc20_uniq_sent_addr',
    'erc20_uniq_rec_addr',
    'erc20_uniq_rec_contract_addr',
    'erc20_min_val_rec',
    'erc20_max_val_rec',
    'erc20_avg_val_rec',
    'erc20_min_val_sent',
    'erc20_max_val_sent',
    'erc20_avg_val_sent',
    'erc20_uniq_sent_token_name',
    'erc20_uniq_rec_token_name',
}

CATEGORICAL_INPUTS: list[str] = [" ERC20 most sent token type", " ERC20_most_rec_token_type"]


class PredictRequest(BaseModel):
    """39 raw model input features. No FLAG, no Address — extras are rejected."""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    avg_min_between_sent_tnx: Annotated[float, Field(alias='Avg min between sent tnx', description='numeric model feature')]
    avg_min_between_received_tnx: Annotated[float, Field(alias='Avg min between received tnx', description='numeric model feature')]
    time_diff_between_first_and_last_mins: Annotated[float, Field(alias='Time Diff between first and last (Mins)', description='numeric model feature')]
    sent_tnx: Annotated[float, Field(alias='Sent tnx', description='numeric model feature')]
    received_tnx: Annotated[float, Field(alias='Received Tnx', description='numeric model feature')]
    number_of_created_contracts: Annotated[float, Field(alias='Number of Created Contracts', description='numeric model feature')]
    unique_received_from_addresses: Annotated[float, Field(alias='Unique Received From Addresses', description='numeric model feature')]
    unique_sent_to_addresses: Annotated[float, Field(alias='Unique Sent To Addresses', description='numeric model feature')]
    min_value_received: Annotated[float, Field(alias='min value received', description='numeric model feature')]
    max_value_received: Annotated[float, Field(alias='max value received ', description='numeric model feature')]
    avg_val_received: Annotated[float, Field(alias='avg val received', description='numeric model feature')]
    min_val_sent: Annotated[float, Field(alias='min val sent', description='numeric model feature')]
    max_val_sent: Annotated[float, Field(alias='max val sent', description='numeric model feature')]
    avg_val_sent: Annotated[float, Field(alias='avg val sent', description='numeric model feature')]
    min_value_sent_to_contract: Annotated[float, Field(alias='min value sent to contract', description='numeric model feature')]
    max_val_sent_to_contract: Annotated[float, Field(alias='max val sent to contract', description='numeric model feature')]
    avg_value_sent_to_contract: Annotated[float, Field(alias='avg value sent to contract', description='numeric model feature')]
    total_transactions_including_tnx_to_create_contract: Annotated[float, Field(alias='total transactions (including tnx to create contract', description='numeric model feature')]
    total_ether_sent: Annotated[float, Field(alias='total Ether sent', description='numeric model feature')]
    total_ether_received: Annotated[float, Field(alias='total ether received', description='numeric model feature')]
    total_ether_sent_contracts: Annotated[float, Field(alias='total ether sent contracts', description='numeric model feature')]
    total_ether_balance: Annotated[float, Field(alias='total ether balance', description='numeric model feature')]
    total_erc20_tnxs: Annotated[float, Field(alias=' Total ERC20 tnxs', description='numeric model feature')]
    erc20_total_ether_received: Annotated[float, Field(alias=' ERC20 total Ether received', description='numeric model feature')]
    erc20_total_ether_sent: Annotated[float, Field(alias=' ERC20 total ether sent', description='numeric model feature')]
    erc20_total_ether_sent_contract: Annotated[float, Field(alias=' ERC20 total Ether sent contract', description='numeric model feature')]
    erc20_uniq_sent_addr: Annotated[float, Field(alias=' ERC20 uniq sent addr', description='numeric model feature')]
    erc20_uniq_rec_addr: Annotated[float, Field(alias=' ERC20 uniq rec addr', description='numeric model feature')]
    erc20_uniq_rec_contract_addr: Annotated[float, Field(alias=' ERC20 uniq rec contract addr', description='numeric model feature')]
    erc20_min_val_rec: Annotated[float, Field(alias=' ERC20 min val rec', description='numeric model feature')]
    erc20_max_val_rec: Annotated[float, Field(alias=' ERC20 max val rec', description='numeric model feature')]
    erc20_avg_val_rec: Annotated[float, Field(alias=' ERC20 avg val rec', description='numeric model feature')]
    erc20_min_val_sent: Annotated[float, Field(alias=' ERC20 min val sent', description='numeric model feature')]
    erc20_max_val_sent: Annotated[float, Field(alias=' ERC20 max val sent', description='numeric model feature')]
    erc20_avg_val_sent: Annotated[float, Field(alias=' ERC20 avg val sent', description='numeric model feature')]
    erc20_uniq_sent_token_name: Annotated[float, Field(alias=' ERC20 uniq sent token name', description='numeric model feature')]
    erc20_uniq_rec_token_name: Annotated[float, Field(alias=' ERC20 uniq rec token name', description='numeric model feature')]
    erc20_most_sent_token_type: Annotated[str, Field(alias=' ERC20 most sent token type', max_length=120, description='token type category')]
    erc20_most_rec_token_type: Annotated[str, Field(alias=' ERC20_most_rec_token_type', max_length=120, description='token type category')]

    @field_validator(*NUMERIC_FIELDS, mode="after")
    @classmethod
    def _finite(cls, v: float) -> float:
        import math
        if not math.isfinite(v):
            raise ValueError("must be a finite number")
        return v



class TopFactor(BaseModel):
    """One SHAP factor. Labeled as model contribution, not causal explanation."""
    model_config = ConfigDict(populate_by_name=True)
    feature: str = Field(description="model feature name")
    value: str = Field(description="raw input value for this feature")
    shap_value: float = Field(description="SHAP value in log-odds units; sign gives direction")
    direction: Literal["increases_risk", "decreases_risk"]
    explanation_type: Literal["model_contribution"] = "model_contribution"


class PredictionResponse(BaseModel):
    prediction: Literal["FRAUD", "LEGITIMATE"]
    fraud_probability: float = Field(ge=0.0, le=1.0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    threshold: float
    top_factors: list[TopFactor]
    prediction_id: str
    model_version: str


class BatchPredictionItem(BaseModel):
    row: int
    prediction: Literal["FRAUD", "LEGITIMATE"]
    fraud_probability: float = Field(ge=0.0, le=1.0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    error: str | None = None


class BatchPredictionResponse(BaseModel):
    n_rows: int
    n_fraud: int
    n_legitimate: int
    n_errors: int
    results: list[BatchPredictionItem]
    model_version: str
