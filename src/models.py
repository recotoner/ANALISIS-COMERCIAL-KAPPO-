from dataclasses import dataclass


@dataclass(frozen=True)
class KeyColumnDetection:
    key: str
    label: str
    aliases: list[str]
    detected_column: str | None


@dataclass(frozen=True)
class ColumnDetectionResult:
    fields: list[KeyColumnDetection]

    def get(self, key: str) -> KeyColumnDetection | None:
        return next((field for field in self.fields if field.key == key), None)

    def has(self, key: str) -> bool:
        field = self.get(key)
        return bool(field and field.detected_column)

    @property
    def found_fields(self) -> list[KeyColumnDetection]:
        return [field for field in self.fields if field.detected_column]

    @property
    def missing_fields(self) -> list[KeyColumnDetection]:
        return [field for field in self.fields if not field.detected_column]


@dataclass(frozen=True)
class AnalysisLevel:
    level: int
    name: str
    description: str


@dataclass(frozen=True)
class AnalysisCapabilities:
    available: list[str]
    unavailable: list[str]


@dataclass(frozen=True)
class DocumentQualityMetrics:
    total_unique_documents: int
    multiline_documents: int
    possible_exact_duplicates: int
    possible_exact_duplicate_rows: int
    document_column: str | None
    comparison_columns: list[str]


@dataclass(frozen=True)
class SkuCoverageMetrics:
    total_rows: int
    valid_sku_rows: int
    empty_sku_rows: int
    valid_sku_row_percentage: float
    valid_sku_sales: float
    empty_sku_sales: float
    valid_sku_sales_percentage: float
    empty_sku_sales_percentage: float
    empty_sku_with_profitability_rows: int
    empty_sku_with_profitability_sales: float
    empty_sku_profitability_amount: float | None
    sku_column: str | None
    amount_column: str | None
    profitability_column: str | None


@dataclass(frozen=True)
class ProfitabilityCoverageMetrics:
    total_rows: int
    valid_sales_amount_rows: int
    valid_cost_rows: int
    valid_margin_rows: int
    zero_cost_rows: int
    null_cost_rows: int
    null_margin_rows: int
    negative_margin_rows: int
    total_sales: float
    sales_with_valid_cost: float
    sales_without_valid_cost: float
    valid_cost_sales_percentage: float
    without_valid_cost_sales_percentage: float
    total_margin_amount: float | None
    calculated_commercial_margin: float | None
    profitability_coverage_level: str
    cost_column: str | None
    margin_column: str | None
    amount_column: str | None
