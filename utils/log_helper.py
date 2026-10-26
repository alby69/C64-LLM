def log_step(logs_list: list, message: str) -> str:
    """Logs a message by printing it and appending it to logs_list."""
    print(message)
    if logs_list is not None:
        logs_list.append(message)
    return message
