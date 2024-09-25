import sys
import iyaml
import qcall
from typing import Any, Dict, List, Set, Optional


REQUIRE_KEYWORD = 'require'


def get_require_list(stage: Dict[str, Any]) -> List[str]:
    if REQUIRE_KEYWORD not in stage:
        return []
    if not isinstance(stage[REQUIRE_KEYWORD], list):
        return [stage[REQUIRE_KEYWORD]]
    return stage[REQUIRE_KEYWORD]


def get_stages(
        task: Dict[str, Any],
        stage_name: str,
        awaiting: Optional[Set[str]] = None,
        result: Optional[List[str]] = None
        ) -> List[str]:
    result = list() if result is None else result
    if stage_name in result:
        return result
    if stage_name not in task:
        raise ValueError(f'Stage not found: {stage_name}')
    stage = task[stage_name]
    awaiting = set() if awaiting is None else awaiting
    if stage_name in awaiting:
        raise ValueError(f'Cyclic requirement: {stage_name}')
    awaiting.add(stage_name)
    for required_stage_name in get_require_list(stage):
        get_stages(task, required_stage_name, awaiting, result)
    awaiting.remove(stage_name)
    result.append(stage_name)
    return result


def apply_context(value, context):
    if isinstance(value, str):
        if value.startswith('$$'):
            return value[1:]
        elif value.startswith('$'):
            return context[value[1:]]
    return value


def execute_stage(task, stage_name, context):
    if stage_name not in task:
        raise ValueError(f'Stage not found: {stage_name}')
    for key, value in task[stage_name].items():
        if key == REQUIRE_KEYWORD:
            continue
        args = []
        kwargs = {}
        if isinstance(value, list):
            args = value
        elif isinstance(value, dict):
            kwargs = value
        elif value is not None:
            args = [value]
        args = [apply_context(arg, context) for arg in args]
        kwargs = {k: apply_context(v, context) for k, v in kwargs.items()}
        kwargs[qcall.QCALL_CONTEXT] = context
        context[stage_name] = qcall.call(key, *args, **kwargs)
        break


def execute_task(task, target_name, context=None):
    context = context or dict()
    execute_list = get_stages(task, target_name)
    for stage_name in execute_list:
        execute_stage(task, stage_name, context)
    return context


def execute_task_file(task_path, target_name, context=None):
    task = iyaml.load(task_path)
    return execute_task(task, target_name, context)


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 -m mline task.yaml target')
        sys.exit(1)
    task_path = sys.argv[1]
    target_name = sys.argv[2] if len(sys.argv) > 2 else 'all'
    execute_task_file(task_path, target_name)
