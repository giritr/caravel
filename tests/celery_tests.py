"""Unit tests for Caravel Celery worker"""
import imp
import json
import subprocess
import os
import pandas as pd
import unittest

import caravel
from caravel import app, appbuilder, db, models, tasks, utils


class CeleryConfig(object):
    BROKER_URL = 'sqla+sqlite:////tmp/celerydb.sqlite'
    CELERY_IMPORTS = ('caravel.tasks',)
    CELERY_RESULT_BACKEND = 'db+sqlite:////tmp/celery_results.sqlite'
    CELERY_ANNOTATIONS = {'tasks.add': {'rate_limit': '10/s'}}
app.config['CELERY_CONFIG'] = CeleryConfig

BASE_DIR = app.config.get('BASE_DIR')
cli = imp.load_source('cli', BASE_DIR + '/bin/caravel')


class UtilityFunctionTests(unittest.TestCase):
    def test_create_table_as(self):
        select_query = "SELECT * FROM outer_space;"
        updated_select_query = tasks.create_table_as(select_query, "tmp")
        self.assertEqual(
            "CREATE TABLE tmp AS SELECT * FROM outer_space;",
            updated_select_query)

        updated_select_query_with_drop = tasks.create_table_as(
            select_query, "tmp", override=True)
        self.assertEqual(
            "DROP TABLE IF EXISTS tmp;\n"
            "CREATE TABLE tmp AS SELECT * FROM outer_space;",
            updated_select_query_with_drop)

        select_query_no_semicolon = "SELECT * FROM outer_space"
        updated_select_query_no_semicolon = tasks.create_table_as(
            select_query_no_semicolon, "tmp")
        self.assertEqual(
            "CREATE TABLE tmp AS SELECT * FROM outer_space",
            updated_select_query_no_semicolon)

        incorrect_query = "SMTH WRONG SELECT * FROM outer_space"
        updated_incorrect_query = tasks.create_table_as(incorrect_query, "tmp")
        self.assertEqual(incorrect_query, updated_incorrect_query)

        insert_query = "INSERT INTO stomach VALUES (beer, chips);"
        updated_insert_query = tasks.create_table_as(insert_query, "tmp")
        self.assertEqual(insert_query, updated_insert_query)

        multi_line_query = (
            "SELECT * FROM planets WHERE\n"
            "Luke_Father = 'Darth Vader';")
        updated_multi_line_query = tasks.create_table_as(
            multi_line_query, "tmp")
        expected_updated_multi_line_query = (
            "CREATE TABLE tmp AS SELECT * FROM planets WHERE\n"
            "Luke_Father = 'Darth Vader';")
        self.assertEqual(
            expected_updated_multi_line_query,
            updated_multi_line_query)

        updated_multi_line_query_with_drop = tasks.create_table_as(
            multi_line_query, "tmp", override=True)
        expected_updated_multi_line_query_with_drop = (
            "DROP TABLE IF EXISTS tmp;\n"
            "CREATE TABLE tmp AS SELECT * FROM planets WHERE\n"
            "Luke_Father = 'Darth Vader';")
        self.assertEqual(
            expected_updated_multi_line_query_with_drop,
            updated_multi_line_query_with_drop)

        delete_query = "DELETE FROM planet WHERE name = 'Earth'"
        updated_delete_query = tasks.create_table_as(delete_query, "tmp")
        self.assertEqual(delete_query, updated_delete_query)

        create_table_as = (
            "CREATE TABLE pleasure AS SELECT chocolate FROM lindt_store;\n")
        updated_create_table_as = tasks.create_table_as(
            create_table_as, "tmp")
        self.assertEqual(create_table_as, updated_create_table_as)

        sql_procedure = (
            "CREATE PROCEDURE MyMarriage\n                "
            "BrideGroom Male (25) ,\n                "
            "Bride Female(20) AS\n                "
            "BEGIN\n                "
            "SELECT Bride FROM ukraine_ Brides\n                "
            "WHERE\n                  "
            "FatherInLaw = 'Millionaire' AND Count(Car) > 20\n"
            "                  AND HouseStatus ='ThreeStoreyed'\n"
            "                  AND BrideEduStatus IN "
            "(B.TECH ,BE ,Degree ,MCA ,MiBA)\n                  "
            "AND Having Brothers= Null AND Sisters =Null"
        )
        updated_sql_procedure = tasks.create_table_as(sql_procedure, "tmp")
        self.assertEqual(sql_procedure, updated_sql_procedure)

        multiple_statements = """
          DROP HUSBAND;
          SELECT * FROM politicians WHERE clue > 0;
          INSERT INTO MyCarShed VALUES('BUGATTI');
          SELECT standard_disclaimer, witty_remark FROM company_requirements;
          select count(*) from developer_brain;
        """
        updated_multiple_statements = tasks.create_table_as(
            multiple_statements, "tmp")
        self.assertEqual(multiple_statements, updated_multiple_statements)


class CeleryTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(CeleryTestCase, self).__init__(*args, **kwargs)
        self.client = app.test_client()

    @classmethod
    def setUpClass(cls):
        try:
            os.remove(app.config.get('SQL_CELERY_DB_FILE_PATH'))
        except OSError as e:
            app.logger.warn(str(e))
        try:
            os.remove(app.config.get('SQL_CELERY_RESULTS_DB_FILE_PATH'))
        except OSError as e:
            app.logger.warn(str(e))

        utils.init(caravel)
        admin = appbuilder.sm.find_user('admin')
        if not admin:
            appbuilder.sm.add_user(
                'admin', 'admin', ' user', 'admin@fab.org',
                appbuilder.sm.find_role('Admin'),
                password='general')
        cli.load_examples(load_test_data=True)

        worker_command = BASE_DIR + '/bin/caravel worker'
        subprocess.Popen(
            worker_command, shell=True, stdout=subprocess.PIPE)

    @classmethod
    def tearDownClass(cls):
        main_db = db.session.query(models.Database).filter_by(
            database_name="main").first()
        main_db.get_sqla_engine().execute("DELETE FROM query;")

        subprocess.call(
            "ps auxww | grep 'celeryd' | awk '{print $2}' | xargs kill -9",
            shell=True
        )
        subprocess.call(
            "ps auxww | grep 'caravel worker' | awk '{print $2}' | "
            "xargs kill -9",
            shell=True
        )

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def login(self, username='admin', password='general'):
        resp = self.client.post(
            '/login/',
            data=dict(username=username, password=password),
            follow_redirects=True)
        assert 'Welcome' in resp.data.decode('utf-8')

    def logout(self):
        self.client.get('/logout/', follow_redirects=True)

    def run_sql(self, dbid, sql, select_as_cta='False', tmp_table_name='tmp'):
        self.login()
        resp = self.client.post(
            '/caravel/sql_json/',
            data=dict(
                database_id=dbid,
                sql=sql,
                select_as_cta=select_as_cta,
                tmp_table_name=tmp_table_name,
            ),
        )
        self.logout()
        return json.loads(resp.data.decode('utf-8'))

    def test_add_limit_to_the_query(self):
        query_session = tasks.get_session()
        db_to_query = query_session.query(models.Database).filter_by(
            id=1).first()
        eng = db_to_query.get_sqla_engine()

        select_query = "SELECT * FROM outer_space;"
        updated_select_query = tasks.add_limit_to_the_sql(
            select_query, 100, eng)
        # Different DB engines have their own spacing while compiling
        # the queries, that's why ' '.join(query.split()) is used.
        # In addition some of the engines do not include OFFSET 0.
        self.assertTrue(
            "SELECT * FROM (SELECT * FROM outer_space;) AS inner_qry "
            "LIMIT 100" in ' '.join(updated_select_query.split())
        )

        select_query_no_semicolon = "SELECT * FROM outer_space"
        updated_select_query_no_semicolon = tasks.add_limit_to_the_sql(
            select_query_no_semicolon, 100, eng)
        self.assertTrue(
            "SELECT * FROM (SELECT * FROM outer_space) AS inner_qry "
            "LIMIT 100" in
            ' '.join(updated_select_query_no_semicolon.split())
        )

        incorrect_query = "SMTH WRONG SELECT * FROM outer_space"
        updated_incorrect_query = tasks.add_limit_to_the_sql(
            incorrect_query, 100, eng)
        self.assertEqual(incorrect_query, updated_incorrect_query)

        insert_query = "INSERT INTO stomach VALUES (beer, chips);"
        updated_insert_query = tasks.add_limit_to_the_sql(
            insert_query, 100, eng)
        self.assertEqual(insert_query, updated_insert_query)

        multi_line_query = (
            "SELECT * FROM planets WHERE\n Luke_Father = 'Darth Vader';"
        )
        updated_multi_line_query = tasks.add_limit_to_the_sql(
            multi_line_query, 100, eng)
        self.assertTrue(
            "SELECT * FROM (SELECT * FROM planets WHERE "
            "Luke_Father = 'Darth Vader';) AS inner_qry LIMIT 100" in
            ' '.join(updated_multi_line_query.split())
        )

        delete_query = "DELETE FROM planet WHERE name = 'Earth'"
        updated_delete_query = tasks.add_limit_to_the_sql(
            delete_query, 100, eng)
        self.assertEqual(delete_query, updated_delete_query)

        create_table_as = (
            "CREATE TABLE pleasure AS SELECT chocolate FROM lindt_store;\n")
        updated_create_table_as = tasks.add_limit_to_the_sql(
            create_table_as, 100, eng)
        self.assertEqual(create_table_as, updated_create_table_as)

        sql_procedure = (
            "CREATE PROCEDURE MyMarriage\n                "
            "BrideGroom Male (25) ,\n                "
            "Bride Female(20) AS\n                "
            "BEGIN\n                "
            "SELECT Bride FROM ukraine_ Brides\n                "
            "WHERE\n                  "
            "FatherInLaw = 'Millionaire' AND Count(Car) > 20\n"
            "                  AND HouseStatus ='ThreeStoreyed'\n"
            "                  AND BrideEduStatus IN "
            "(B.TECH ,BE ,Degree ,MCA ,MiBA)\n                  "
            "AND Having Brothers= Null AND Sisters = Null"
        )
        updated_sql_procedure = tasks.add_limit_to_the_sql(
            sql_procedure, 100, eng)
        self.assertEqual(sql_procedure, updated_sql_procedure)

    def test_run_async_query_delay_get(self):
        main_db = db.session.query(models.Database).filter_by(
            database_name="main").first()
        eng = main_db.get_sqla_engine()

        # Case 1.
        # DB #0 doesn't exist.
        result1 = self.run_sql(
            0,
            'SELECT * FROM dontexist',
            tmp_table_name='tmp_table_1_a',
            select_as_cta='True',
        )
        expected_result1 = {
            'error': 'Database with id 0 is missing.',
            'status': models.QueryStatus.FAILED,
        }
        self.assertEqual(
            sorted(expected_result1.items()),
            sorted(result1.items())
        )
        session1 = db.create_scoped_session()
        query1 = session1.query(models.Query).filter_by(
            sql='SELECT * FROM dontexist').first()
        self.assertIsNone(query1)
        session1.close()

        # Case 2.
        # Table doesn't exist.
        result2 = self.run_sql(
            1,
            'SELECT * FROM dontexist1',
            tmp_table_name='tmp_table_2_a',
            select_as_cta='True',
        )
        self.assertTrue('error' in result2)
        session2 = db.create_scoped_session()
        query2 = session2.query(models.Query).filter_by(
            sql='SELECT * FROM dontexist1').first()
        self.assertEqual(models.QueryStatus.FAILED, query2.status)
        session2.close()

        # Case 3.
        # Table and DB exists, CTA call to the backend.
        where_query = (
            "SELECT name FROM ab_permission WHERE name='can_select_star'")
        result3 = self.run_sql(
            1,
            where_query,
            tmp_table_name='tmp_table_3_a',
            select_as_cta='True',
        )
        expected_result3 = {
            u'query_id': 2,
            u'status': models.QueryStatus.FINISHED,
            u'columns': [u'name'],
            u'data': [{u'name': u'can_select_star'}],
        }
        self.assertEqual(
            sorted(expected_result3.items()),
            sorted(result3.items())
        )
        session3 = db.create_scoped_session()
        query3 = session3.query(models.Query).filter_by(
            sql=where_query).first()
        session3.close()
        df3 = pd.read_sql_query(sql="SELECT * FROM tmp_table_3_a", con=eng)
        data3 = df3.to_dict(orient='records')
        self.assertEqual(models.QueryStatus.FINISHED, query3.status)
        self.assertEqual([{'name': 'can_select_star'}], data3)

        # Case 4.
        # Table and DB exists, CTA call to the backend, no data.
        result4 = self.run_sql(
            1,
            'SELECT * FROM ab_permission WHERE id=666',
            tmp_table_name='tmp_table_4_a',
            select_as_cta='True',
        )
        expected_result4 = {
            u'query_id': 3,
            u'status': models.QueryStatus.FINISHED,
            u'columns': [u'id', u'name'],
            u'data': [],
        }
        self.assertEqual(
            sorted(expected_result4.items()),
            sorted(result4.items())
        )
        session4 = db.create_scoped_session()
        query4 = session4.query(models.Query).filter_by(
            sql='SELECT * FROM ab_permission WHERE id=666').first()
        session4.close()
        df4 = pd.read_sql_query(sql="SELECT * FROM tmp_table_4_a", con=eng)
        data4 = df4.to_dict(orient='records')
        self.assertEqual(models.QueryStatus.FINISHED, query4.status)
        self.assertEqual([], data4)

        # Case 5.
        # Table and DB exists, select without CTA.
        result5 = self.run_sql(
            1,
            where_query,
            tmp_table_name='tmp_table_5_a',
            select_as_cta='False',
        )
        expected_result5 = {
            u'query_id': 4,
            u'columns': [u'name'],
            u'data': [{u'name': u'can_select_star'}],
            u'status': models.QueryStatus.FINISHED,
        }
        self.assertEqual(
            sorted(expected_result5.items()),
            sorted(result5.items())
        )


if __name__ == '__main__':
    unittest.main()
