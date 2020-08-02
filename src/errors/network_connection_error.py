# coding: utf-8


class NoInternetError(Exception):
    """Exception raised for errors when the Internet connection is lost."""

    def __init__(self, message: str):
        """Constructor for NoInternetError class.

        :param message: Error message passed when raising this exception.
        :type message: str
        """
        self.message = message
