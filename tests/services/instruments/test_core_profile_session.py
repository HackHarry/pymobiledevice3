from pymobiledevice3.services.dvt.instruments.core_profile_session_tap import CoreProfileSessionTap
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService


def test_stackshot(lockdown):
    """
    Test getting stackshot.
    :param pymobiledevice3.lockdown.LockdownClient lockdown: Lockdown client.
    """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        with CoreProfileSessionTap(dvt, CoreProfileSessionTap.get_time_config(dvt)) as tap:
            data = tap.get_stackshot()

    assert 'Darwin Kernel' in data['osversion']
    # Constant kernel task data.
    assert data['task_snapshots'][0]['task_snapshot']['ts_pid'] == 0
    assert data['task_snapshots'][0]['task_snapshot']['ts_p_comm'] == 'kernel_task'


def test_watch_events(lockdown):
    """
    Test getting realtime kdebug events.
    :param pymobiledevice3.lockdown.LockdownClient lockdown: Lockdown client.
    """
    events_count = 10
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        with CoreProfileSessionTap(dvt, CoreProfileSessionTap.get_time_config(dvt)) as tap:
            events = list(tap.watch_events(events_count))

    assert len(events) == events_count
