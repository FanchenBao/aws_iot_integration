# coding: utf-8

from collections import defaultdict

from multiprocessing import Event, Process
from typing import Callable, Dict


class ChildProcesses(object):
    """A class to handle all child processes."""

    def __init__(self):
        """Constructor."""
        # Format of child_processes is:
        # {p_name: {process: process_obj, term_event: termination event}}
        self.child_processes: Dict[str, Dict] = defaultdict(dict)

    def create(
        self,
        p_name: str,
        target_fun: Callable,
        *non_term_event_args,
    ) -> None:
        """Create a child process and place it in the child_processes dict.

        The child process MUST accept a termination event as its last arg.

        :param p_name: Name of the child process.
        :type p_name: str
        :param target_fun: The function to be run in a child process
        :type target_fun: Callable
        :param non_term_event_args: The arguments to be passed to the process
            that does NOT contain the termination event.
        """
        term_event = Event()
        self.child_processes[p_name]['process'] = Process(
            target=target_fun,
            args=(*non_term_event_args, term_event),
        )
        self.child_processes[p_name]['term_event'] = term_event

    def create_and_start(
        self,
        p_name: str,
        target_fun: Callable,
        *non_term_event_args,
    ) -> None:
        """Create a child process and start it right after.

        :param p_name: Name of the child process.
        :type p_name: str
        :param target_fun: The function to be run in a child process
        :type target_fun: Callable
        :param non_term_event_args: The arguments to be passed to the process
            that does NOT contain the termination event.
        """
        self.create(p_name, target_fun, *non_term_event_args)
        self.child_processes[p_name]['process'].start()

    def terminate(self, p_name: str):
        """Terminate a child process specified by p_name.

        :param p_name: Name of the child process.
        :type p_name: str
        """
        self.child_processes[p_name]['term_event'].set()
        self.child_processes[p_name]['process'].join()
