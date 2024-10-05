.. _error_target:

Error Target
============

Error targets are those endpoints that receive forwarded errors from Arch when issues arise,
such as failing to properly call a function/API, detecting violations of guardrails, or encountering other processing errors.
These errors are communicated to the application via headers (X-Arch-[ERROR-TYPE]), allowing it to handle the errors gracefully
and take appropriate actions.
