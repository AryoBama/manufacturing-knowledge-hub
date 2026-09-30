class ManufacturingHubError(Exception):
    """Base exception for Manufacturing Knowledge Hub."""
    def __init__(self, message: str = "Internal pipeline error", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QueryValidationError(ManufacturingHubError):
    def __init__(self, message: str = "Invalid query or malformed parameters"):
        super().__init__(message, status_code=400)


class ResourceNotFoundError(ManufacturingHubError):
    def __init__(self, message: str = "Requested plant equipment or document not found"):
        super().__init__(message, status_code=404)


class EvidenceInsufficientError(ManufacturingHubError):
    def __init__(self, message: str = "Insufficient approved technical evidence"):
        super().__init__(message, status_code=422)


class PipelineExecutionError(ManufacturingHubError):
    def __init__(self, message: str = "Pipeline processing failure"):
        super().__init__(message, status_code=500)
