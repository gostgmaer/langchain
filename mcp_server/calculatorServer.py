from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool()
def add(a: float, b: float) -> float:
    """__summary__
    Adds two numbers.
    """
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """__summary__
    Subtracts two numbers.
    """
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """__summary__
    Multiplies two numbers.
    """
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """__summary__
    Divides two numbers.
    """
    return a / b


@mcp.tool()
def modulus(a: float, b: float) -> float:
    """
    Returns the remainder when the first number is divided by the second.

    Args:
        a: Dividend.
        b: Divisor.

    Returns:
        The remainder of a % b.
    """
    return a % b



## The Transport ="stdio"
# Standard stdid/stdout/stderr to recived and response to tool functions call


if __name__ == "__main__":
    mcp.run(transport="stdio")