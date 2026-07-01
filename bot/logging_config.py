import logging
import os
import sys

def setup_logging(log_file="trading_bot.log"):
    """
    Sets up logging configuration.
    - Detailed debug/info logs are written to the specified log_file.
    - Clean, user-friendly logs are written to standard output (console).
    """
    # Create the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything at root level

    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. File Handler (Detailed Logging)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] (%(name)s:%(filename)s:%(lineno)d) - %(message)s'
    )
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not configure file logging to {log_file}: {e}", file=sys.stderr)

    # 2. Console Handler (User-facing Logging)
    class ConsoleFormatter(logging.Formatter):
        # ANSI Escape Sequences for terminal styling
        GREY = "\033[90m"
        BLUE = "\033[94m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        GREEN = "\033[92m"
        RESET = "\033[0m"
        BOLD = "\033[1m"

        def format(self, record):
            # Map log levels to symbols and colors
            if record.levelno == logging.ERROR or record.levelno == logging.CRITICAL:
                prefix = f"{self.RED}{self.BOLD}[ERROR]{self.RESET} "
            elif record.levelno == logging.WARNING:
                prefix = f"{self.YELLOW}{self.BOLD}[WARNING]{self.RESET} "
            elif record.levelno == logging.INFO:
                if record.msg.startswith("SUCCESS:") or "successfully" in record.msg.lower():
                    prefix = f"{self.GREEN}{self.BOLD}[SUCCESS]{self.RESET} "
                else:
                    prefix = f"{self.BLUE}[INFO]{self.RESET} "
            else:
                prefix = f"{self.GREY}[DEBUG]{self.RESET} "
            
            # Format message
            formatted_msg = super().format(record)
            return f"{prefix}{formatted_msg}"

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Keep console clean, hide raw debug logs unless needed
    console_handler.setFormatter(ConsoleFormatter('%(message)s'))
    root_logger.addHandler(console_handler)

    # Suppress verbose requests/urllib3 logging to file
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    return root_logger
