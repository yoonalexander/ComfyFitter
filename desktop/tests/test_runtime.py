from pathlib import Path
from unittest.mock import Mock

import pytest

from desktop.runtime import Services


def ready():
    return {'application':'comfyfitter','deployment_mode':'local','comfyui':{'ready':True}}


def services(tmp_path):
    (tmp_path/'frontend/dist').mkdir(parents=True)
    (tmp_path/'frontend/dist/index.html').write_text('app')
    runtime=Services(tmp_path,timeout=1,sleep=lambda _:None)
    runtime.worker_root=Mock(return_value=tmp_path/'worker')
    runtime.worker_matches=Mock(return_value=True)
    runtime.launch=Mock()
    return runtime


def test_ready_services_are_reused_without_launching_or_submitting(monkeypatch,tmp_path):
    runtime=services(tmp_path);runtime.health=Mock(return_value=ready())
    monkeypatch.setattr('desktop.runtime.port_open',lambda _:True)
    assert runtime.ensure()['state']=='ready'
    runtime.launch.assert_not_called()


def test_occupied_foreign_port_is_preserved(monkeypatch,tmp_path):
    runtime=services(tmp_path);runtime.health=Mock(return_value=None)
    monkeypatch.setattr('desktop.runtime.port_open',lambda _:True)
    assert runtime.ensure()['state']=='error'
    assert 'No process was stopped' in runtime.status()['message']
    runtime.launch.assert_not_called()


def test_unrelated_worker_is_not_reused_or_stopped(monkeypatch,tmp_path):
    runtime=services(tmp_path);runtime.health=Mock(return_value=ready());runtime.worker_matches.return_value=False
    monkeypatch.setattr('desktop.runtime.port_open',lambda _:True)
    assert runtime.ensure()['state']=='error'
    assert 'different GPU service' in runtime.status()['message']
    runtime.launch.assert_not_called()


def test_retry_does_not_duplicate_a_worker_that_is_still_starting(tmp_path):
    runtime=Services(tmp_path)
    existing=Mock();existing.poll.return_value=None;runtime.processes['gpu']=existing
    assert runtime.launch('gpu',['never run'],tmp_path,{}) is existing


def test_concurrent_retry_returns_existing_status_without_launch(tmp_path):
    runtime=services(tmp_path);runtime.lock.acquire()
    assert runtime.ensure()['state']=='starting'
    runtime.launch.assert_not_called();runtime.lock.release()


def test_startup_failure_is_visible_and_can_be_retried(monkeypatch,tmp_path):
    runtime=services(tmp_path);runtime.health=Mock(side_effect=RuntimeError('Unexpected application'))
    monkeypatch.setattr('desktop.runtime.port_open',lambda _:True)
    assert runtime.ensure()=={'state':'error','message':'Unexpected application'}
    runtime.health=Mock(return_value=ready())
    assert runtime.ensure()['state']=='ready'


def test_desktop_rejects_hosted_health(monkeypatch,tmp_path):
    response=Mock();response.json.return_value={**ready(),'deployment_mode':'hosted'}
    client=Mock();client.get.return_value=response
    context=Mock();context.__enter__=Mock(return_value=client);context.__exit__=Mock(return_value=False)
    monkeypatch.setattr('desktop.runtime.httpx.Client',Mock(return_value=context))
    with pytest.raises(RuntimeError,match='hosted configuration'):
        Services(tmp_path).health()
