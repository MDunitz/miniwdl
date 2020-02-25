"""
Caching outputs of task calls based on inputs.
"""
import hashlib
import json
import os

from WDL import Env, Value, values_to_json

from typing import Optional


def get_input_cache(key: str, run_dir: str) -> Optional[Env.Bindings[Value.Base]]:
    """
    Resolve cache key to call outputs, if available, or None.
    """
    # find file
    try:
        with open(os.path.join(run_dir, f"{key}.json"), "rb") as file_reader:
            contents = file_reader.read()
    except FileNotFoundError:
        return None
    return json.loads(contents)


def put_input_cache(key: str, run_dir: str, outputs: Env.Bindings[Value.Base]) -> None:
    """
    Store call outputs for future reuse
    """
    with open(os.path.join(run_dir, f"{key}.json"), "w") as outfile:
        print(
            json.dumps(values_to_json(outputs)),
            file=outfile,
        )


def get_digest_for_inputs(inputs):
    """
    Return sha256 for json of sorted inputs
    :param inputs: WDL inputs for the task
    :return: digest
    """
    json_inputs = json.dumps(sorted(values_to_json(inputs))).encode('utf-8')
    return hashlib.sha256(json_inputs).hexdigest()
