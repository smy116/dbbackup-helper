import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.backup_manager import BackupManager
from app.plugins.base import DatabasePlugin
from app.plugins.mysql import MySQLPlugin
from app.plugins.postgresql import PostgreSQLPlugin
from app.webhook import NotifyMuxNotifier, send_backup_notification


class DummyPlugin(DatabasePlugin):
    def __init__(self, temp_dir, databases=None, dump_errors=None, list_error=None, extra_error=None):
        super().__init__({'enabled': True}, temp_dir)
        self.databases = databases or []
        self.dump_errors = dump_errors or {}
        self.list_error = list_error
        self.extra_error = extra_error

    @property
    def db_type(self):
        return 'dummy'

    def is_enabled(self):
        return True

    def get_databases(self):
        if self.list_error:
            raise RuntimeError(self.list_error)
        return self.databases

    def backup_database(self, database, output_file):
        if database in self.dump_errors:
            raise RuntimeError(self.dump_errors[database])
        with open(output_file, 'w') as f:
            f.write(database)
        return True

    def backup_extra(self):
        if self.extra_error:
            raise RuntimeError(self.extra_error)
        return []


class BackupFailureTests(unittest.TestCase):
    def test_list_databases_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = DummyPlugin(temp_dir, list_error='connect failed')

            result = plugin.backup_all_databases()

            self.assertEqual(result['files'], [])
            self.assertEqual(len(result['failed']), 1)
            self.assertEqual(result['failed'][0]['stage'], 'list_databases')
            self.assertIn('connect failed', result['failed'][0]['error'])

    def test_empty_database_list_is_not_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = DummyPlugin(temp_dir, databases=[])

            result = plugin.backup_all_databases()

            self.assertEqual(result['files'], [])
            self.assertEqual(result['failed'], [])

    def test_mysql_list_command_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = MySQLPlugin(
                {
                    'enabled': True,
                    'host': 'mysql',
                    'port': 3306,
                    'user': 'root',
                    'password': '',
                    'databases': 'all',
                    'extra_opts': '',
                },
                temp_dir,
            )
            failed_mysql = SimpleNamespace(returncode=1, stdout='', stderr='cannot connect')

            with patch('app.plugins.mysql.subprocess.run', return_value=failed_mysql):
                result = plugin.backup_all_databases()

            self.assertEqual(result['files'], [])
            self.assertEqual(len(result['failed']), 1)
            self.assertEqual(result['failed'][0]['stage'], 'list_databases')
            self.assertIn('cannot connect', result['failed'][0]['error'])

    def test_mysql_empty_auto_database_list_is_not_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = MySQLPlugin(
                {
                    'enabled': True,
                    'host': 'mysql',
                    'port': 3306,
                    'user': 'root',
                    'password': '',
                    'databases': 'all',
                    'extra_opts': '',
                },
                temp_dir,
            )
            only_system_dbs = SimpleNamespace(
                returncode=0,
                stdout='information_schema\nmysql\nperformance_schema\nsys\n',
                stderr='',
            )

            with patch('app.plugins.mysql.subprocess.run', return_value=only_system_dbs):
                result = plugin.backup_all_databases()

            self.assertEqual(result['files'], [])
            self.assertEqual(result['failed'], [])

    def test_single_database_dump_failure_is_recorded_and_successes_continue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = DummyPlugin(
                temp_dir,
                databases=['app', 'broken'],
                dump_errors={'broken': 'dump failed'},
            )

            result = plugin.backup_all_databases()

            self.assertEqual(len(result['files']), 1)
            self.assertTrue(result['files'][0].endswith('app.sql'))
            self.assertEqual(len(result['failed']), 1)
            self.assertEqual(result['failed'][0]['database'], 'broken')
            self.assertEqual(result['failed'][0]['stage'], 'dump')

    def test_all_database_dump_failures_are_recorded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = DummyPlugin(
                temp_dir,
                databases=['app', 'logs'],
                dump_errors={'app': 'app failed', 'logs': 'logs failed'},
            )

            result = plugin.backup_all_databases()

            self.assertEqual(result['files'], [])
            self.assertEqual(len(result['failed']), 2)
            self.assertEqual({item['database'] for item in result['failed']}, {'app', 'logs'})

    def test_postgresql_globals_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = PostgreSQLPlugin(
                {
                    'enabled': True,
                    'host': 'postgres',
                    'port': 5432,
                    'user': 'postgres',
                    'password': '',
                    'databases': 'app',
                    'extra_opts': '',
                },
                temp_dir,
            )

            def write_dump(_database, output_file):
                with open(output_file, 'w') as f:
                    f.write('dump')
                return True

            failed_pg_dumpall = SimpleNamespace(returncode=1, stdout='', stderr='globals failed')
            with patch.object(plugin, 'backup_database', side_effect=write_dump), \
                 patch('app.plugins.postgresql.subprocess.run', return_value=failed_pg_dumpall):
                result = plugin.backup_all_databases()

            self.assertEqual(len(result['files']), 1)
            self.assertEqual(len(result['failed']), 1)
            self.assertEqual(result['failed'][0]['stage'], 'extra')
            self.assertIn('globals failed', result['failed'][0]['error'])

    def test_backup_manager_records_plugin_failures_and_still_uploads_successes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SimpleNamespace(
                rclone_remote='backup',
                rclone_config=os.path.join(temp_dir, 'rclone.conf'),
                rclone_insecure_skip_verify=False,
                temp_dir=temp_dir,
                backup_encrypt=False,
                backup_password='',
                backup_retention_days=7,
                postgresql_enabled=False,
                mysql_enabled=False,
                mariadb_enabled=False,
                mongodb_enabled=False,
                redis_enabled=False,
            )
            with open(config.rclone_config, 'w') as f:
                f.write('[backup]\ntype = local\n')

            manager = BackupManager(config)
            manager.plugins = [
                DummyPlugin(
                    temp_dir,
                    databases=['app', 'broken'],
                    dump_errors={'broken': 'dump failed'},
                )
            ]
            manager.rclone = SimpleNamespace(
                upload_file=Mock(return_value=True),
                cleanup_old_backups=Mock(return_value=True),
            )

            with patch('app.backup_manager.create_backup_archive', side_effect=lambda files, output, password=None: _write_archive(output)):
                result = manager.run_backup()

            self.assertEqual(len(result['success']), 1)
            self.assertEqual(len(result['failed']), 1)
            self.assertEqual(result['failed'][0]['database'], 'broken')
            manager.rclone.upload_file.assert_called_once()


class NotificationTests(unittest.TestCase):
    def test_failed_item_format_includes_database_and_stage(self):
        notifier = NotifyMuxNotifier('https://notify.example', 'secret', 'job')
        payload = notifier.format_notification(
            {
                'success': [],
                'failed': [
                    {
                        'type': 'mysql',
                        'database': 'app',
                        'stage': 'dump',
                        'error': 'dump failed',
                    }
                ],
                'start_time': datetime(2026, 1, 1, 0, 0, 0),
                'end_time': datetime(2026, 1, 1, 0, 0, 1),
            }
        )

        self.assertIn('mysql/app [dump]: dump failed', payload['body'])
        self.assertEqual(payload['metadata']['failed'][0]['database'], 'app')
        self.assertEqual(payload['metadata']['failed'][0]['stage'], 'dump')

    def test_notification_is_skipped_when_there_are_no_failures(self):
        config = SimpleNamespace(notifymux_api_key='secret', notifymux_endpoint='https://notify.example')
        result = send_backup_notification({'failed': []}, config)
        self.assertTrue(result)

    def test_notification_is_sent_when_failures_exist(self):
        config = SimpleNamespace(
            notifymux_api_key='secret',
            notifymux_endpoint='https://notify.example',
            notifymux_job_name='job',
        )
        results = {
            'success': [],
            'failed': [{'type': 'mysql', 'database': 'app', 'stage': 'dump', 'error': 'failed'}],
            'start_time': datetime(2026, 1, 1, 0, 0, 0),
            'end_time': datetime(2026, 1, 1, 0, 0, 1),
        }
        response = SimpleNamespace(status_code=200, text='ok')

        with patch('app.webhook.requests.post', return_value=response) as post:
            result = send_backup_notification(results, config)

        self.assertTrue(result)
        post.assert_called_once()


def _write_archive(output_file):
    with open(output_file, 'w') as f:
        f.write('archive')
    return output_file


if __name__ == '__main__':
    unittest.main()
