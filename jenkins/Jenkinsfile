pipeline {
  options {
    buildDiscarder(logRotator(numToKeepStr: '10')) // Retain history on the last 10 builds
    ansiColor('xterm') // Enable colors in terminal
    timestamps() // Append timestamps to each line
    timeout(time: 20, unit: 'MINUTES') // Set a timeout on the total execution time of the job
  }
  agent {
    // Run this job within a Docker container built using Dockerfile.build
    // contained within your projects repository. This image should include
    // the core runtimes and dependencies required to run the job,
    // for example Python 3.x and NPM.
    dockerfile { filename 'Dockerfile.build' }
  }
  stages {  // Define the individual processes, or stages, of your CI pipeline
    stage('Checkout') { // Checkout (git clone ...) the projects repository
      steps {
        checkout scm
      }
    }
    stage('Setup') { // Install any dependencies you need to perform testing
      steps {
        script {
          sh """
          pip install -r requirements.txt
          """
        }
      }
    }
    stage('Linting') { // Run pylint against your code
      steps {
        script {
          sh """
          pylint **/*.py
          """
        }
      }
    }
    stage('Unit Testing') { // Perform unit testing
      steps {
        script {
          sh """
          python -m unittest discover -s tests/unit
          """
        }
      }
    }
    stage('Integration Testing') { //Perform integration testing
      steps {
        script {
          sh """
          # You have the option to stand up a temporary environment to perform
          # these tests and/or run the tests against an existing environment. The
          # advantage to the former is you can ensure the environment is clean
          # and in a desired initial state. The easiest way to stand up a temporary
          # environment is to use Docker and a wrapper script to orchestrate the
          # process. This script will handle standing up supporting services like
          # MySQL & Redis, running DB migrations, starting the web server, etc.
          # You can utilize your existing automation, your custom scripts and Make.
          ./standup_testing_environment.sh # Name this whatever you'd like

          python -m unittest discover -s tests/integration
        """
      }
    }
  }
  post {
    failure {
      script {
        msg = "Build error for ${env.JOB_NAME} ${env.BUILD_NUMBER} (${env.BUILD_URL})"

        slackSend message: msg, channel: env.SLACK_CHANNEL
    }
  }
}