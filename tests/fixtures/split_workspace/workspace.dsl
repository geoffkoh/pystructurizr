workspace "Split Workspace" "Model spread across included files" {

    model {
        !include model/people.dsl
        !include model/systems.dsl
    }

    views {
        systemContext core Context "Context" {
            include *
            autoLayout
        }
    }
}
