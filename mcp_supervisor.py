import asyncio

from mcp import ClientSession
from mcp.client.stdio import stdio_client


class McpSupervisor:
    """Keeps one connection to the tool server (mcp_server.py) alive.

    One background task opens the connection, checks on it every few seconds,
    and opens a fresh one if the tool server stops answering.
    Everything happens inside that one task, because the MCP library needs a
    connection to be opened and closed by the same task.
    """

    def __init__(self, server_params, check_interval=20, check_timeout=5,
                 failures_before_restart=2, retry_delay=3):
        self._params = server_params
        self._check_interval = check_interval
        self._check_timeout = check_timeout
        self._failures_before_restart = failures_before_restart
        self._retry_delay = retry_delay

        self.session = None          # the live connection, or None while down
        self.restart_count = 0       # how many times we had to reconnect
        self._ready = asyncio.Event()
        self._wake = asyncio.Event()
        self._stop_flag = False
        self._restart_flag = False
        self._task = None

    async def start(self, wait_seconds=30):
        """Starts the background task and waits until the first connection is up."""
        self._task = asyncio.create_task(self._run())
        try:
            await asyncio.wait_for(self._ready.wait(), wait_seconds)
        except asyncio.TimeoutError:
            print("Tool server was not ready yet - the supervisor will keep trying.")

    async def stop(self):
        self._stop_flag = True
        self._wake.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, 10)
            except Exception:
                self._task.cancel()

    def request_restart(self):
        """Asks for a fresh connection as soon as possible."""
        self._restart_flag = True
        self._wake.set()

    async def is_healthy(self):
        """True if the tool server answers a simple question within a few seconds."""
        session = self.session
        if session is None:
            return False
        try:
            await asyncio.wait_for(session.list_tools(), self._check_timeout)
            return True
        except Exception:
            return False

    async def _run(self):
        while not self._stop_flag:
            try:
                async with stdio_client(self._params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await asyncio.wait_for(session.initialize(), 30)
                        self.session = session
                        self._ready.set()
                        print("Tool server connected")
                        await self._watch()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Tool server connection problem: {e}")
            finally:
                self.session = None
                self._ready.clear()
            if not self._stop_flag:
                print(f"Reconnecting to the tool server in {self._retry_delay} seconds")
                await asyncio.sleep(self._retry_delay)

    async def _watch(self):
        """Stays inside the open connection until it is time to close it."""
        bad_checks = 0
        while True:
            if self._stop_flag:
                return
            if self._restart_flag:
                self._restart_flag = False
                self.restart_count += 1
                print("Restart requested - opening a fresh tool server connection")
                return
            try:
                await asyncio.wait_for(self._wake.wait(), self._check_interval)
                self._wake.clear()
                continue
            except asyncio.TimeoutError:
                pass

            if await self.is_healthy():
                bad_checks = 0
            else:
                bad_checks += 1
                print(f"Tool server health check failed ({bad_checks} in a row)")
                if bad_checks >= self._failures_before_restart:
                    self.restart_count += 1
                    print("Tool server is not answering - restarting it")
                    return