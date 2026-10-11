# Deskmate

Deskmate is a service desk web app: requesters raise tickets, support officers resolve them, and each role has an AI feature.

- [User Guide](docs/UserGuide.md)
- [Developer Guide](docs/DeveloperGuide.md)
- [Reflections](docs/Reflections.md)

## How we build it

We use spec-driven development with role agents that can each write only their own part of the repository. Start with [`workflow/README.md`](workflow/README.md); the rules agents follow are in [`AGENTS.md`](AGENTS.md).
