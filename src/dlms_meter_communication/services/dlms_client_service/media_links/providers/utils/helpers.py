import ipaddress


def validate_ip_address(ip_address: str) -> None:
    """
    Validate that the provided IP address is valid.

    Args:
        ip_address (str): IP address to validate

    Raises:
        ValueError: If IP address is invalid
        TypeError: If IP address is not a string
    """
    if not isinstance(ip_address, str):
        raise TypeError("IP address must be a string")

    if not ip_address.strip():
        raise ValueError("IP address cannot be empty")

    try:
        ipaddress.ip_address(ip_address)
    except ValueError as e:
        raise ValueError(f"Invalid IP address '{ip_address}': {e}") from e


def validate_port(port: int) -> None:
    """
    Validate that the provided port number is valid.

    Args:
        port (int): Port number to validate

    Raises:
        ValueError: If port is out of valid range
        TypeError: If port is not an integer
    """
    if not isinstance(port, int):
        raise TypeError("Port must be an integer")

    if not (1 <= port <= 65535):
        raise ValueError(f"Port must be between 1 and 65535, got {port}")
