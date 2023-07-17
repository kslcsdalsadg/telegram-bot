from time import sleep

import docker
import logging
import os

logger = logging.getLogger(__name__)

class DockerUtils():
    DATA = { 'client': None }
    CONFIG = { 'max-wait-time-for-container-stop': 30, 'max-wait-time-for-container-deletion': 30, 'wait-time-for-container-start': 60 }
       
    @staticmethod
    def _get_client(): 
        if DockerUtils.DATA['client'] == None:
            DockerUtils.DATA['client'] = docker.from_env()
        return DockerUtils.DATA['client']

    @staticmethod
    def initialize():
        pass
    
    @staticmethod
    def get_containers(all = True):
        containers = []
        client = DockerUtils._get_client()
        for container in client.containers.list(all = all):
            containers.append(container)
        return containers

    @staticmethod
    def _get_container(id):
        try:
            return DockerUtils._get_client().containers.get(id)
        except:
            return None

    @staticmethod
    def get_container(id):
        container = DockerUtils._get_container(id)
        if container is None:
            raise Exception('Container %s not found' % ( id ))
        return container
        
    @staticmethod
    def is_container_running(id):
        return DockerUtils.get_container(id).status == 'running'

    @staticmethod
    def get_container_name(id):
        return DockerUtils.get_container(id).name

    @staticmethod
    def stop_container(id):
        if DockerUtils.is_container_running(id):
            container = DockerUtils.get_container(id)
            container.stop()
            for i in range(DockerUtils.CONFIG['max-wait-time-for-container-stop']):
                sleep(1)
                if not DockerUtils.is_container_running(id):
                    return True
            return False
        return True

    @staticmethod
    def _get_compose_file(id, do_not_check_if_file_exists):
        data = docker.APIClient(base_url = 'unix://var/run/docker.sock').inspect_container(id)
        if ('Config' in data) and ('Labels' in data['Config']) and ('com.docker.compose.project.working_dir' in data['Config']['Labels']) and ('com.docker.compose.project.config_files' in data['Config']['Labels']):
            docker_compose_file = data['Config']['Labels']['com.docker.compose.project.config_files']
            if not docker_compose_file.startswith(data['Config']['Labels']['com.docker.compose.project.working_dir']):
                docker_compose_file = '%s/%s' % ( data['Config']['Labels']['com.docker.compose.project.working_dir'], docker_compose_file )
            if do_not_check_if_file_exists or os.path.exists(docker_compose_file):
                return docker_compose_file
        return None

    @staticmethod
    def _execute_docker_compose_command(docker_compose_file, command, host_indirection, delay_before_return = 0):
        command = 'docker-compose -f %s %s' % ( docker_compose_file, command )
        if host_indirection:
            command = 'ssh %s %s' % ( host_indirection, command )
        logger.info('Intentando ejecutar un comando de sistema: ' + command)
        if os.system(command) == 0:
            if delay_before_return > 0:
                sleep(delay_before_return)
            return True
        return False
        

    @staticmethod
    def pull_container(id, host_indirection = None):
        if not DockerUtils.is_container_running(id):
            docker_compose_file = DockerUtils._get_compose_file(id, host_indirection is not None)
            if docker_compose_file is not None:
                return DockerUtils._execute_docker_compose_command(docker_compose_file, 'pull', host_indirection, 10)
        return False

    @staticmethod
    def start_container(id, host_indirection = None):
        if not DockerUtils.is_container_running(id):
            docker_compose_file = DockerUtils._get_compose_file(id, host_indirection is not None)
            if docker_compose_file is not None:
                if DockerUtils._execute_docker_compose_command(docker_compose_file, 'up -d', host_indirection):
                    for i in range(DockerUtils.CONFIG['wait-time-for-container-start']):
                        sleep(1)
                        if DockerUtils.is_container_running(id):
                            break
                    return True
            return False
        return True
                    
    @staticmethod
    def restart_container(id, host_indirection = None):
        if DockerUtils.stop_container(id):
            return DockerUtils.start_container(id, host_indirection)
        return False

    @staticmethod
    def container_exists(id):
        return DockerUtils._get_container(id) is not None
        
    @staticmethod
    def delete_container(id):
        if not DockerUtils.is_container_running(id):
            container = DockerUtils.get_container(id)
            container.remove()
            for i in range(DockerUtils.CONFIG['max-wait-time-for-container-deletion']):
                sleep(1)
                if not DockerUtils.container_exists(id): 
                    return True
        return False
                
