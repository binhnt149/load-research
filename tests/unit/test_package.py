def test_package_identifies_reproducible_method_version():
    from load_research import METHOD_VERSION, __version__

    assert __version__ == "0.1.4rc2"
    assert METHOD_VERSION == "class-profile-v3"
