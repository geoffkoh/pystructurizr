core = softwareSystem "Core System" "Does the work" {
    api = container "API" "Serves requests" "Python, FastAPI"
}

// Nested include: relationships live one level deeper.
!include relationships.dsl
