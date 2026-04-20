# Security Policy

## Supported versions

Only the latest released minor version of `weather-decoder` receives security
fixes. Older releases will not be patched.

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| < 1.1   | :x:                |

## Reporting a vulnerability

Please **do not** report security vulnerabilities through public GitHub
issues, discussions, or pull requests.

Instead, report them privately using GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
on this repository:

1. Go to the **Security** tab of the repository.
2. Click **Report a vulnerability**.
3. Fill in the form with as much detail as possible.

A useful report includes:

- A description of the issue and its impact.
- Steps to reproduce, or a proof-of-concept input/script.
- The affected version(s) and platform.
- Any suggested mitigation if you have one.

## Response process

- We aim to acknowledge new reports within **5 business days**.
- Once triaged, we will work on a fix and coordinate a release.
- Credit will be given to the reporter in the release notes unless anonymity
  is requested.

## Scope

This policy covers the `weather-decoder` Python package and its CLI tools in
this repository. It does not cover third-party dependencies; please report
vulnerabilities in those projects to their respective maintainers.
