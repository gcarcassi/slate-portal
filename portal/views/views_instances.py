from portal.decorators import authenticated
from portal import app
import json
import requests
from flask import (flash, redirect, render_template,
                   request, session, url_for, jsonify)
from connect_api import (list_instances_request,
                        list_user_groups,
                        list_users_instances_request,
                        get_user_access_token)
# Read endpoint and token from config file
slate_api_token = app.config['SLATE_API_TOKEN']
slate_api_endpoint = app.config['SLATE_API_ENDPOINT']


@app.route('/instances_ajax', methods=['GET'])
def instances_ajax():
    instances = list_instances_request()
    return jsonify(instances)


@app.route('/users_instances_ajax', methods=['GET'])
def users_instances_ajax():
    instances = list_users_instances_request(session)
    return jsonify(instances)


@app.route('/instances', methods=['GET'])
@authenticated
def list_instances():
    """
    - List deployed application instances on SLATE
    """
    if request.method == 'GET':
        return render_template('instances.html')


@app.route('/instances-xhr', methods=['GET'])
@authenticated
def list_instances_xhr():
    """
    - List User's Instances Registered on SLATE (json response)
    """
    if request.method == 'GET':
        instances = list_instances_request()
        user_groups_list = list_user_groups(session)
        user_groups = []
        for groups in user_groups_list:
            user_groups.append(groups['metadata']['name'])
        return jsonify(instances, user_groups)


@app.route('/instances/<name>', methods=['GET'])
@authenticated
def view_instance(name):
    """
    - View detailed instance information on SLATE
    """
    access_token = get_user_access_token(session)
    query = {'token': access_token}
    if request.method == 'GET':

        # Initialize separate list queries for multiplex request
        instance_detail_query = '/v1alpha3/instances/' + name + '?token=' + query['token'] + '&detailed'
        instance_log_query = '/v1alpha3/instances/' + name + '/logs' + '?token=' + query['token']
        # Set up multiplex JSON
        multiplexJson = {instance_detail_query: {"method":"GET"},
                            instance_log_query: {"method":"GET"}}
        # POST request for multiplex return
        multiplex = requests.post(
            slate_api_endpoint + '/v1alpha3/multiplex', params=query, json=multiplexJson)
        multiplex = multiplex.json()
        # Parse post return for instance, instance details, and instance logs
        instance_details = json.loads(multiplex[instance_detail_query]['body'])
        instance_log = json.loads(multiplex[instance_log_query]['body'])

        instance_status = True

        if instance_details['kind'] == 'Error':
            instance_status = False
            return render_template('404.html')

        # pretty_print = json.dumps(instance_details, sort_keys = True, indent = 2)
        # print(pretty_print)

        return render_template('instance_profile.html', name=name,
                                instance_details=instance_details,
                                instance_status=instance_status,
                                instance_log=instance_log)


@app.route('/instances-log-xhr/<name>/<container>/<lines>', methods=['GET'])
@authenticated
def get_instance_container_log(name, container, lines):
    access_token = get_user_access_token(session)
    query = {'token': access_token}
    # Initialize instance log query for multiplex request
    instance_log_query = '/v1alpha3/instances/' + name + '/logs' + '?token=' + query['token'] + '&container=' + container + '&max_lines=' + lines
    # Set up multiplex JSON
    multiplexJson = {instance_log_query: {"method":"GET"}}
    # POST request for multiplex return
    multiplex = requests.post(
        slate_api_endpoint + '/v1alpha3/multiplex', params=query, json=multiplexJson)
    multiplex = multiplex.json()
    # Parse post return for instance, instance details, and instance logs
    instance_log = json.loads(multiplex[instance_log_query]['body'])

    return jsonify(instance_log['logs'])


@app.route('/instances/<name>/delete_instance', methods=['GET'])
@authenticated
def delete_instance(name):
    access_token = get_user_access_token(session)
    query = {'token': access_token}

    r = requests.delete(slate_api_endpoint + '/v1alpha3/instances/' + name, params=query)
    if r.status_code == requests.codes.ok:
        flash('Successfully deleted instance', 'success')
    else:
        flash('Failed to delete instance', 'warning')

    return redirect(url_for('list_instances'))
