from base64 import b64decode, b64encode

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class TransactionJournal(InMemorySaver):
    """Replay saver calls from one durable workflow row.

    A bounded synchronous run persists the journal with its local side effects.
    Only server-generated journals are loaded. No pickle serializer is enabled.
    """

    def __init__(self, journal: list | None = None):
        super().__init__(serde=JsonPlusSerializer(allowed_json_modules=(), allowed_msgpack_modules=()))
        self.journal = list(journal or [])
        for method, kind, payload in self.journal:
            args = self.serde.loads_typed((kind, b64decode(payload)))
            if method == "put":
                super().put(*args)
            elif method == "writes":
                super().put_writes(*args)
            else:
                raise ValueError("Unknown checkpoint journal entry")

    def _record(self, method, args):
        kind, payload = self.serde.dumps_typed(args)
        self.journal.append([method, kind, b64encode(payload).decode("ascii")])

    def _checkpoint_config(self, config):
        return {"configurable": {
            key: config["configurable"][key]
            for key in ("thread_id", "checkpoint_ns", "checkpoint_id")
            if key in config["configurable"]
        }}

    def put(self, config, checkpoint, metadata, new_versions):
        values = {**checkpoint, "channel_values": dict(checkpoint["channel_values"])}
        args = (self._checkpoint_config(config), values, dict(metadata), dict(new_versions))
        result = super().put(*args)
        self._record("put", args)
        return result

    def put_writes(self, config, writes, task_id, task_path=""):
        args = (self._checkpoint_config(config), list(writes), task_id, task_path)
        super().put_writes(*args)
        self._record("writes", args)
