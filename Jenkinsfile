pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        COMPOSE_PROJECT_NAME = 'devops-lab'
    }

    stages {
        stage('Checkout') {
            steps {
                sh 'ls -la'
                sh 'docker --version'
            }
        }

        stage('Build') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose up -d'
            }
        }

        stage('Smoke test') {
            steps {
                sh 'sleep 5'
                sh 'docker compose ps'
                sh 'curl -f http://backend:8000/tasks'      
            }
        }
    }

    post {
        success {
            echo 'Deploy OK'
        }
        failure {
            sh 'docker compose logs --tail=50 || true'
        }
    }
}