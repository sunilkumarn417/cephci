def nodeName = "centos-7"
def ciMessage = ""

node(nodeName) {

    stage('Checkout') {
        if (env.WORKSPACE) {
            deleteDir()
        }
        checkout([
            $class: 'GitSCM',
            branches: [[name: '*/test-release-info']],
            doGenerateSubmoduleConfigurations: false,
            extensions: [[
                $class: 'CloneOption',
                shallow: true,
                noTags: false,
                reference: '',
                depth: 0
            ]],
            submoduleCfg: [],
            userRemoteConfigs: [[
                url: 'https://github.com/sunilkumarn417/cephci.git']]
        ])
    }

    stage('Execute'){
        ciMessage = "${params.CI_MESSAGE}" ?: ""
        println "${ciMessage}"
    }
}
