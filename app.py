## https://medium.com/@fareedkhandev/create-desktop-application-using-flask-framework-ee4386a583e9
## https://github.com/ClimenteA/flaskwebgui/blob/master/examples/flask-desktop/main.py

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flaskwebgui import FlaskUI
from datetime import datetime, timedelta, date
import sqlite3
import yaml
import os
import markdown
import traceback

app = Flask(__name__)

with open("config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

appconfig = {'title': None}
appconfig['version'] = "1.0.1.0"  ### Hauptversion.Nebenversion.Revisionsnummer.Buildnummer

## Create Database if not exisits
def create_db():
    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()
        # Person Tabe
        cursor.execute("CREATE TABLE IF NOT EXISTS person (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, surname TEXT NOT NULL, lastname TEXT NOT NULL, mail TEXT, workhours NUMERIC NOT NULL, workpercentage INTEGER NOT NULL)")
        cursor.execute("CREATE INDEX IF NOT EXISTS person_id ON person (id)")
        connection.commit()

        # Team Table
        cursor.execute("CREATE TABLE IF NOT EXISTS team (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, name TEXT NOT NULL, lead INTEGER REFERENCES person (id), colead INTEGER REFERENCES person (id), warning INTEGER, min INTEGER, max INTEGER)")
        cursor.execute("CREATE INDEX IF NOT EXISTS team_id ON team (id)")
        connection.commit()

        # Person Team Mapping Table
        cursor.execute("CREATE TABLE IF NOT EXISTS person_team_mapping (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, person INTEGER REFERENCES person (id) NOT NULL, team INTEGER REFERENCES team (id) NOT NULL, percentage INTEGER NOT NULL)")
        cursor.execute("CREATE INDEX IF NOT EXISTS mapping_id ON person_team_mapping (id)")
        connection.commit()

        ## Absence Table
        cursor.execute("CREATE TABLE absence (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, startdate TEXT NOT NULL, enddate TEXT NOT NULL, percentage INTEGER NOT NULL, person INTEGER REFERENCES person (id) NOT NULL)")
        cursor.execute("CREATE INDEX IF NOT EXISTS absence_id ON absence (id)")
        connection.commit()

        update_db_1()

    except Exception as e:
        print("Error on creating Database")
        print(f"An error occurred: {e}")
    finally:
        connection.close()

def update_db_1():
    try:
        connection_update = sqlite3.connect(cfg["database"])

        cursor_update = connection_update.cursor()

        ## Config Table
        cursor_update.execute("CREATE TABLE config (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, configname TEXT NOT NULL, configvalue TEXT NOT NULL)")
        cursor_update.execute("CREATE INDEX IF NOT EXISTS config_id ON config (id)")
        connection_update.commit()

        ## Set DB Version
        sql = ''' INSERT INTO config(configname, configvalue) VALUES(?, ?) '''
        data = ("db_version", appconfig['version'])
        cursor_update.execute(sql, data)
        connection_update.commit()

        ## Set DB Creation Date
        sql = ''' INSERT INTO config(configname, configvalue) VALUES(?, ?) '''
        data = ("db_creation", str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')))
        cursor_update.execute(sql, data)
        connection_update.commit()

    except Exception as e:
        print("Error on update Database 1")
        print(f"An error occurred: {e}")
    finally:
        connection_update.close()

def check_requirements():
    if not os.path.exists(cfg["database"]):
        print('Database not exists, create empty Database.')
        database_path = os.path.dirname(cfg["database"])
        print(database_path)
        if not os.path.exists(database_path):
            os.makedirs(database_path)
        create_db()
    else:
        print('Database exists')

    ## Database Update
    try:
        connection = sqlite3.connect(cfg["database"])
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE name='config'")
        result = cursor.fetchone()
        if result is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT configname, configvalue FROM config WHERE configname = 'db_version'")
            result2 = cursor.fetchone()

            if (result2[1] != appconfig['version']):
                if result2[1] == '1.0.0.0':
                    update_db_1()
        else:
            update_db_1()

    except Exception as e:
        print("Update failed!")
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
    finally:
        connection.close()

@app.route('/' , methods=['GET', 'POST'])
def root():
    appconfig['title'] = "Übersicht"

    view = {}
    view['url'] = "/"
    if request.method == 'GET':
        view['startdate'] =  str(datetime.today().strftime('%d.%m.%Y'))
        enddate = date.today() + timedelta(days=int(cfg["view-size"]))
        view['enddate'] = str(enddate.strftime('%d.%m.%Y'))
    else:
        view['startdate'] = request.values.get('start')
        view['enddate'] = request.values.get('end')

    teams = []

    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM team")

        rows = cursor.fetchall()

        rowcount = 0

        for row in rows:
            team_details = {'id': None, 'name': None, 'lead': None, 'colead': None, 'warning': None, 'min': None, 'max': None}
            team_details['id'] = row[0]
            team_details['name'] = row[1]

            cursor.execute("SELECT count() as anzahl FROM person_team_mapping WHERE team='" + str(row[0]) + "'")
            membercount = cursor.fetchone()
            if membercount[0] == 1:
                team_details['member'] = str(membercount[0]) + " Person"
            else:
                team_details['member'] = str(membercount[0]) + " Personen"

            if row[2] == None:
                team_details['leadid'] = 0
                team_details['lead'] = "Keine Leitung"
            else:
                cursor.execute("SELECT surname, lastname FROM person WHERE id='" + str(row[2]) + "'")
                lead = cursor.fetchone()
                team_details['leadid'] = row[2]
                team_details['lead'] = lead[0] + " " + lead[1]

            if row[3] == None:
                team_details['colead'] = "Kein Vertreter"
                team_details['coleadid'] = 0
            else:
                cursor.execute("SELECT surname, lastname FROM person WHERE id='" + str(row[3]) + "'")
                colead = cursor.fetchone()
                team_details['coleadid'] = row[3]
                team_details['colead'] = colead[0] + " " + colead[1]

            if row[4] == None:
                team_details['warning'] = ""
            else:
                team_details['warning'] = row[4]

            if row[5] == None:
                team_details['min'] = ""
            else:
                team_details['min'] = row[5]

            if row[6] == None:
                team_details['max'] = ""
            else:
                team_details['max'] = row[6]

            if rowcount == 0:
                team_details['chartclass'] = "team-chart-first"
                team_details['infoclass'] = "team-info-first"
                rowcount += 1

            cursor = connection.cursor()
            cursor.execute("SELECT id, person, team, percentage FROM person_team_mapping WHERE team='" + str(row[0]) + "'")

            mapping_rows = cursor.fetchall()

            day_team_worktime = 0
            team_absence = []
            for mapping_row in mapping_rows:
                cursor = connection.cursor()
                cursor.execute("SELECT workhours, workpercentage FROM person WHERE id='" + str(mapping_row[1]) + "'")

                person_work = cursor.fetchone()

                person_effective_workhours = int(str(person_work[0])) * (int(str(person_work[1])) / 100)
                person_effective_workhours_day = round(((person_effective_workhours * (int(str(mapping_row[3])) / 100)) / int(len(cfg['base-week-workdays']))), 2)
                day_team_worktime = round(day_team_worktime + person_effective_workhours_day, 2)

                cursor = connection.cursor()
                cursor.execute("SELECT startdate, enddate, percentage, person FROM absence WHERE person='" + str(mapping_row[1]) + "'")

                person_absence = cursor.fetchall()
                for absence in person_absence:
                    absence_date_sd = datetime.strptime(absence[0],'%d.%m.%Y')
                    absence_date_ed = datetime.strptime(absence[1],'%d.%m.%Y')
                    absence_delta = absence_date_ed.date() - absence_date_sd.date()

                    for i in range(absence_delta.days + 1):
                        day = absence_date_sd.date() + timedelta(days=i)
                        absence_details = {}
                        absence_details['date'] = day.strftime('%d.%m.%Y')
                        absence_details['time'] = round((person_effective_workhours_day * (int(str(absence[2])) / 100)), 2)
                        absence_details['team'] = mapping_row[2]
                        absence_details['person'] = absence[3]
                        team_absence.append(absence_details)

            date_sd = datetime.strptime(view['startdate'],'%d.%m.%Y')
            date_ed = datetime.strptime(view['enddate'],'%d.%m.%Y')

            delta = date_ed.date() - date_sd.date()
            team_workdays = []
            team_workdays_count = 0
            workday_warning = (int(cfg['base-week-hours']) / int(len(cfg['base-week-workdays']))) * (team_details['warning'] / 100)
            workday_min = (int(cfg['base-week-hours']) / int(len(cfg['base-week-workdays']))) * (team_details['min'] / 100)
            workday_max = (int(cfg['base-week-hours']) / int(len(cfg['base-week-workdays']))) * (team_details['max'] / 100)
            for i in range(delta.days + 1):
                day = date_sd.date() + timedelta(days=i)
                day_name = day.strftime('%A').lower()

                tmp_day_team_worktime = 0.0
                for days in cfg['base-week-workdays']:
                    if days == day_name:
                        tmp_day_team_worktime = day_team_worktime
                        for absence_day in team_absence:
                            if absence_day['date'] == day.strftime('%d.%m.%Y'):
                                tmp_day_team_worktime = round(tmp_day_team_worktime,2) - round(absence_day['time'],2)

                day_details = {'date': day.strftime('%d.%m.%y'), 'dayworkhours':  round(tmp_day_team_worktime,2), 'warning': workday_warning, 'min': workday_min, 'max': workday_max}
                if team_workdays_count == 0:
                    day_details['firstrow'] = True
                    team_workdays_count += 1
                team_workdays.append(day_details)

            team_details['view'] = team_workdays
            teams.append(team_details)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()

    return render_template('root.html', appconfig=appconfig, view=view, teams=teams)

@app.route('/flaskwebgui-keep-server-alive' , methods=['GET'])
def keep_alive():
    return jsonify(success=True)

@app.route('/persons', methods=['GET'])
def person():
    appconfig['title'] = "Personen"

    persons = []

    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM person")

        rows = cursor.fetchall()

        for row in rows:
            person_details = {'id': None, 'surname': None, 'lastname': None, 'mail': None, 'workhours': None, 'workpercentage': None}
            person_details['id'] = row[0]
            person_details['surname'] = row[1]
            person_details['lastname'] = row[2]
            if row[3] == None:
                person_details['mail'] = ""
            else:
                person_details['mail'] = row[3]
            person_details['workhours'] = row[4]
            person_details['workpercentage'] = row[5]
            persons.append(person_details)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()

    return render_template('persons.html', appconfig=appconfig, persons=persons)

@app.route('/person/add', methods=['GET', 'POST'])
def person_add():
    if request.method == 'GET':
        appconfig['title'] = "Person anlegen"
        person = {}
        person['workhours'] = cfg["person"]['workhours']
        person['workpercentage'] = cfg["person"]['workpercentage']
        person['url'] = "/person/add"
        return render_template('person.html', appconfig=appconfig, person=person)
    else:
        surname = request.values.get('surname')
        lastname = request.values.get('lastname')
        mail = request.values.get('mail')
        workhours = request.values.get('workhours')
        workpercentage = request.values.get('workpercentage')

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()

            sql = ''' INSERT INTO person(surname,lastname,mail,workhours,workpercentage) VALUES(?,?,?,?,?) '''
            data = (surname, lastname, mail, workhours, workpercentage)
            cursor.execute(sql, data)

            connection.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()
        return redirect(url_for('person'))

@app.route('/person/absence/<personid>', methods=['GET', 'POST'])
def person_absence(personid):
    if request.method == 'GET':
        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()
            cursor.execute("SELECT surname, lastname FROM person WHERE id = ?", (personid))

            person = cursor.fetchone()

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM absence WHERE person = ? ORDER BY id DESC", (personid))

            appointments = cursor.fetchall()

            appconfig['title'] = "Abwesenheit für " + person[0] + " " + person[1]
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()

        absence = {}
        absence['url'] = "/person/absence/" + personid
        absence['length'] = [{'value':100, 'name': 'Ganzer Tag'}, {'value':50, 'name': 'Halber Tag'}]
        absence['personid'] = personid
        absence['appointments'] = []
        for appointment_row in appointments:
            appointment_details = {'id': None, 'startdate': None, 'enddate': None, 'percentage': None}
            appointment_details['id'] = appointment_row[0]
            appointment_details['start'] = appointment_row[1]
            appointment_details['end'] = appointment_row[2]
            appointment_details['length'] = appointment_row[3]
            absence['appointments'].append(appointment_details)

        return render_template('personabsence.html', appconfig=appconfig, absence=absence)
    else:
        personid = request.values.get('personid')
        startdate = request.values.get('start')
        enddate = request.values.get('end')
        length = request.values.get('length')

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()

            sql = ''' INSERT INTO absence(startdate,enddate,percentage,person) VALUES(?,?,?,?) '''
            data = (startdate, enddate, length, personid)
            cursor.execute(sql, data)

            connection.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()
        return redirect(url_for('person_absence', personid=personid))

@app.route('/person/absencedelete', methods=['POST'])
def person_absencedelete():
    id = request.values.get('appointmentid')
    personid = request.values.get('personid')

    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()

        sql = ''' DELETE FROM absence WHERE id = ? '''
        data = (id)
        cursor.execute(sql, data)

        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()
    return redirect(url_for('person_absence', personid=personid))

@app.route('/person/manageteams/<personid>', methods=['GET', 'POST'])
def person_manageteams(personid):
    if request.method == 'GET':
        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()
            cursor.execute("SELECT surname, lastname FROM person WHERE id = ?", (personid))

            person = cursor.fetchone()

            appconfig['title'] = "Teams zuweisen für " + person[0] + " " + person[1]

            cursor = connection.cursor()
            cursor.execute("SELECT id, name FROM team")

            team_rows = cursor.fetchall()
            team_list = []
            for team_row in team_rows:
                team_details = {'id': None, 'name': None}
                team_details['id'] = team_row[0]
                team_details['name'] = team_row[1]
                team_list.append(team_details)

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM person_team_mapping WHERE person = ?", (personid))

            rows = cursor.fetchall()

            teamcount = 1
            memberof = []

            if len(rows) == 0:
                member_details = {'row': 1, 'percentage': 100}
                member_details['teams'] = team_list
                teamcount = teamcount + 1
                memberof.append(member_details)
            else:
                for row in rows:
                    member_details = {'row': None, 'percentage': None}
                    member_details['row'] = teamcount
                    team_list_selected = []
                    for team_row in team_rows:
                        team_details = {'id': None, 'name': None}
                        team_details['id'] = team_row[0]
                        team_details['name'] = team_row[1]
                        if row[2] == team_row[0]:
                            team_details['selected'] = "selected"
                        team_list_selected.append(team_details)
                    member_details['teams'] = team_list_selected
                    member_details['percentage'] = row[3]
                    teamcount = teamcount + 1
                    memberof.append(member_details)

            person = {}
            person['membercount'] = teamcount
            person['url'] = "/person/manageteams/" + personid

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()

        return render_template('personmanageteams.html', appconfig=appconfig, person=person, teams=team_list, memberof=memberof)
    else:
        teamcount = request.values.get('teamcount')

        mappings = []

        count = 1
        while count <= int(teamcount):
            mapping_add = True
            mapping_add_count = 0
            mapping_count = 0
            for mapping in mappings:
                if mapping['teamid'] == request.values.get('team-' + str(count)):
                    mapping_add = False
                    mapping_add_count = mapping_count
                mapping_count += 1

            if mapping_add == True:
                mapping_details = {'teamid': None, 'percentage': None}
                mapping_details['teamid'] = request.values.get('team-' + str(count))
                mapping_details['percentage'] = request.values.get('percentage-' + str(count))
                mappings.append(mapping_details)
            else:
                mappings[mapping_add_count]['percentage'] = int(mappings[mapping_add_count]['percentage']) + int(request.values.get('percentage-' + str(count)))

            count += 1

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()

            sql = ''' DELETE FROM person_team_mapping WHERE person = ? '''
            data = (personid)
            cursor.execute(sql, data)

            connection.commit()

            for mapping in mappings: 
                cursor = connection.cursor()

                sql = ''' INSERT INTO person_team_mapping(person,team,percentage) VALUES(?,?,?) '''
                data = (personid, int(mapping['teamid']), mapping['percentage'])
                cursor.execute(sql, data)

                connection.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()
        return redirect(url_for('person'))


@app.route('/person/edit/<personid>', methods=['GET', 'POST'])
def person_edit(personid):
    if request.method == 'GET':
        appconfig['title'] = "Person bearbeiten"
        person = {}

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM person WHERE id = '" + personid + "'")

            row = cursor.fetchone()

            person = {'id': None, 'surname': None, 'lastname': None, 'mail': None, 'workhours': None, 'workpercentage': None}
            person['id'] = row[0]
            person['surname'] = row[1]
            person['lastname'] = row[2]
            if row[3] == None:
                person['mail'] = ""
            else:
                person['mail'] = row[3]
            person['workhours'] = row[4]
            person['workpercentage'] = row[5]

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()

        person['url'] = "/person/edit/" + personid
        return render_template('person.html', appconfig=appconfig, person=person)
    else:
        surname = request.values.get('surname')
        lastname = request.values.get('lastname')
        mail = request.values.get('mail')
        workhours = request.values.get('workhours')
        workpercentage = request.values.get('workpercentage')

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()

            sql = ''' UPDATE person SET surname=?,lastname=?,mail=?,workhours=?,workpercentage=? WHERE id = ? '''
            data = (surname, lastname, mail, workhours, workpercentage, personid)
            cursor.execute(sql, data)

            connection.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()
        return redirect(url_for('person'))

@app.route('/person/delete', methods=['POST'])
def person_delete():
    id = request.values.get('personid')

    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()

        sql = ''' DELETE FROM person WHERE id = ? '''
        data = (id)
        cursor.execute(sql, data)

        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()
    return redirect(url_for('person'))

@app.route('/teams')
def teams():
    appconfig['title'] = "Teams"

    teams = []

    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM team")

        rows = cursor.fetchall()

        for row in rows:
            team_details = {'id': None, 'name': None, 'lead': None, 'colead': None, 'warning': None, 'min': None, 'max': None}
            team_details['id'] = row[0]
            team_details['name'] = row[1]

            cursor.execute("SELECT count() as anzahl FROM person_team_mapping WHERE team='" + str(row[0]) + "'")
            membercount = cursor.fetchone()
            team_details['member'] = membercount[0]

            if row[2] == None:
                team_details['leadid'] = 0
                team_details['lead'] = "Keine Leitung"
            else:
                cursor.execute("SELECT surname, lastname FROM person WHERE id='" + str(row[2]) + "'")
                lead = cursor.fetchone()
                team_details['leadid'] = row[2]
                team_details['lead'] = lead[0] + " " + lead[1]

            if row[3] == None:
                team_details['colead'] = "Kein Vertreter"
                team_details['coleadid'] = 0
            else:
                cursor.execute("SELECT surname, lastname FROM person WHERE id='" + str(row[3]) + "'")
                colead = cursor.fetchone()
                team_details['coleadid'] = row[3]
                team_details['colead'] = colead[0] + " " + colead[1]

            if row[4] == None:
                team_details['warning'] = ""
            else:
                team_details['warning'] = row[4]

            if row[5] == None:
                team_details['min'] = ""
            else:
                team_details['min'] = row[5]

            if row[6] == None:
                team_details['max'] = ""
            else:
                team_details['max'] = row[6]
            teams.append(team_details)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()

    return render_template('teams.html', appconfig=appconfig, teams=teams)

@app.route('/team/add', methods=['GET', 'POST'])
def team_add():
    if request.method == 'GET':
        appconfig['title'] = "Team anlegen"
        team = {}
        team['warning'] = cfg["team"]['warning']
        team['max'] = cfg["team"]['max']
        team['min'] = cfg["team"]['min']
        team['url'] = "/team/add"

        persons_lead = []
        persons_colead = []
        persons_member = []

        person_details = {'id': None, 'name': None}
        person_details['id'] = 0
        person_details['name'] = "Keine Leitung"
        persons_lead.append(person_details)

        person_details = {'id': None, 'name': None}
        person_details['id'] = 0
        person_details['name'] = "Kein Vertreter"
        persons_colead.append(person_details)

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()
            cursor.execute("SELECT id, surname, lastname FROM person ORDER BY lastname ASC")

            rows = cursor.fetchall()

            for row in rows:
                person_details = {'id': None, 'name': None}
                person_details['id'] = row[0]
                person_details['name'] = row[1] + " " + row[2]
                persons_lead.append(person_details)
                persons_colead.append(person_details)
                persons_member.append(person_details)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()

        team['lead'] = persons_lead
        team['colead'] = persons_colead
        team['member'] = persons_member
        team['showmemberclass'] = False

        return render_template('team.html', appconfig=appconfig, team=team)
    else:
        name = request.values.get('name')
        lead = request.values.get('lead')
        colead = request.values.get('colead')
        warning = request.values.get('warning')
        min = request.values.get('min')
        max = request.values.get('max')

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()

            sql = ''' INSERT INTO team(name,lead,colead,warning,min,max) VALUES(?,?,?,?,?,?) '''
            data = (name, lead, colead, warning, min, max)
            cursor.execute(sql, data)

            connection.commit()

            teamid = cursor.lastrowid

            if lead == str(0):
                cursor.execute("UPDATE team SET lead=NULL WHERE id =" + str(teamid))
                connection.commit()

            if colead == str(0):
                cursor.execute("UPDATE team SET colead=NULL WHERE id =" + str(teamid))
                connection.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()
        return redirect(url_for('teams'))

@app.route('/team/edit/<teamid>', methods=['GET', 'POST'])
def team_edit(teamid):
    if request.method == 'GET':
        appconfig['title'] = "Team bearbeiten"

        persons_lead = []
        persons_colead = []

        person_details = {'id': None, 'name': None}
        person_details['id'] = 0
        person_details['name'] = "Keine Leitung"
        persons_lead.append(person_details)

        person_details = {'id': None, 'name': None}
        person_details['id'] = 0
        person_details['name'] = "Kein Vertreter"
        persons_colead.append(person_details)

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM team WHERE id = '" + teamid + "'")

            row = cursor.fetchone()

            cursor = connection.cursor()
            cursor.execute("SELECT id, surname, lastname FROM person ORDER BY lastname ASC")

            person_rows = cursor.fetchall()

            team = {'id': None, 'name': None, 'lead': None, 'colead': None, 'warning': None, 'min': None, 'max': None}
            team['id'] = row[0]
            team['name'] = row[1]

            for person_row in person_rows:
                person_details = {'id': None, 'name': None}
                person_details['id'] = person_row[0]
                person_details['name'] = person_row[1] + " " + person_row[2]
                if row[2] == person_row[0]:
                    person_details['selected'] = "selected"
                persons_lead.append(person_details)
            team['lead'] = persons_lead

            for person_row in person_rows:
                person_details = {'id': None, 'name': None}
                person_details['id'] = person_row[0]
                person_details['name'] = person_row[1] + " " + person_row[2]
                if row[3] == person_row[0]:
                    person_details['selected'] = "selected"
                persons_colead.append(person_details)
            team['colead'] = persons_colead

            if row[4] == None:
                team['warning'] = cfg["team"]['warning']
            else:
                team['warning'] = row[4]

            if row[5] == None:
                team['min'] = cfg["team"]['min']
            else:
                team['min'] = row[5]

            if row[6] == None:
                team['max'] = cfg["team"]['max']
            else:
                team['max'] = row[6]

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()

        team['url'] = "/team/edit/" + teamid
        return render_template('team.html', appconfig=appconfig, team=team)
    else:
        name = request.values.get('name')
        lead = request.values.get('lead')
        colead = request.values.get('colead')
        warning = request.values.get('warning')
        min = request.values.get('min')
        max = request.values.get('max')

        try:
            connection = sqlite3.connect(cfg["database"])

            cursor = connection.cursor()

            sql = ''' UPDATE team SET name=?,lead=?,colead=?,warning=?,min=?,max=? WHERE id = ? '''
            data = (name, lead, colead, warning, min, max, teamid)
            cursor.execute(sql, data)

            connection.commit()

            if lead == str(0):
                cursor.execute("UPDATE team SET lead=NULL WHERE id =" + str(teamid))
                connection.commit()

            if colead == str(0):
                cursor.execute("UPDATE team SET colead=NULL WHERE id =" + str(teamid))
                connection.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            connection.close()
        return redirect(url_for('teams'))

@app.route('/team/delete', methods=['POST'])
def team_delete():
    id = request.values.get('teamid')

    try:
        connection = sqlite3.connect(cfg["database"])

        cursor = connection.cursor()

        sql = ''' DELETE FROM team WHERE id = ? '''
        data = (id)
        cursor.execute(sql, data)

        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()
    return redirect(url_for('teams'))

@app.route('/about')
def about():
    appconfig['title'] = "Über"

    with open('CHANGELOG.md', 'r') as f:
        aboutMd= f.read()
    aboutHtml = markdown.markdown(aboutMd)
    f.close()

    return render_template('about.html', appconfig=appconfig, changelog=aboutHtml)

def start_flask(**server_kwargs):
    app = server_kwargs.pop("app", None)
    server_kwargs.pop("debug", None)

    try:
        import waitress

        waitress.serve(app, **server_kwargs, threads=10)
    except:
        app.run(**server_kwargs)


if __name__ == "__main__":
    # app.run(debug=True)

    # Default start flask
    FlaskUI(
        app=app,
        server="flask",
        width=1000,
        height=600,
        on_startup=lambda: check_requirements(),
        on_shutdown=lambda: print("byee")
    ).run()
