from pathlib import Path
import yaml
import ninjarmy
import readline  # noqa: F401 — enables arrow keys and history in input()
from ninjarmy.agents.agent_spec import AgentSpec, AgentCreateSpec
from ninjarmy.core.agent import Agent
from ninjarmy.core.registry import AgentRegistry

_AGENTS_YAML = Path(ninjarmy.__file__).parent / "agents" / "agents.yaml"

class ManagerAgent:
    _instance = None

    def __init__(self):
        existing = AgentRegistry.all()
        self.agent_ids = max((a.id for a in existing), default=0)

    def hire_agent(self, spec: AgentCreateSpec) -> Agent:
        self.agent_ids += 1
        agent = Agent(AgentSpec(name=spec.name, role=spec.role, task=spec.task, id=self.agent_ids))
        AgentRegistry.register(agent)
        agent.start()
        return agent

    def run_repl(self):
        from ninjarmy.core.model import start_session, end_session

        with open(_AGENTS_YAML) as f:
            valid_roles = yaml.safe_load(f)["agents"]

        project = input("Describe your project: > ").strip()
        start_session(project=project)

        print("Session started. Type 'help' for commands.")

        print("Generating project context...")
        from ninjarmy.core.context import generate_project_context, save_context
        context = generate_project_context(project)
        save_context(context)
        print("\n--- Project Context ---")
        print(context)
        print("----------------------\n")

        # future: ask user for more context/refine prompt if needed

        while True:
            try:
                raw = input("manager> ").strip()
            except (EOFError, KeyboardInterrupt):
                end_session()
                print("\nSession terminated.")
                break

            if not raw:
                continue

            parts = raw.split(" -- ", maxsplit=1)
            tokens = parts[0].split()
            task = parts[1].strip() if len(parts) > 1 else ""
            cmd = tokens[0].lower()

            if cmd in ("exit", "quit"):
                end_session()
                print("Session terminated.")
                break

            elif cmd == "hire":
                if len(tokens) < 3:
                    print("Usage: hire <name> <role> [-- <task>]")
                    print(f"Roles: {', '.join(valid_roles)}")
                    continue
                name, role = tokens[1], tokens[2]
                if role not in valid_roles:
                    print(f"Unknown role '{role}'. Valid roles: {', '.join(valid_roles)}")
                    continue
                try:
                    agent = self.hire_agent(AgentCreateSpec(name=name, role=role, task=task))
                    print(f"Hired '{agent.name}' (id:{agent.get_id():04d}) as {role}.")
                except (ValueError, RuntimeError) as e:
                    print(f"ERROR: {e}")

            elif cmd == "agents":
                all_agents = AgentRegistry.all()
                if not all_agents:
                    print("No agents hired yet.")
                else:
                    print(f"{'ID':<6} {'NAME':<16} {'ROLE':<14} {'STATUS':<10} TASK")
                    print("-" * 70)
                    for a in all_agents:
                        print(f"{a.id:<6} {a.name:<16} {a.role:<14} {a.get_status():<10} {a.task}")

            elif cmd == "help":
                print("Commands:")
                print("  hire <name> <role> [-- <task>]   Hire a new agent")
                print("  agents                            List all agents")
                print("  roles                             List all possible roles")
                print("  help                              Show this message")
                print("  exit                              End the session")
                print(f"  Roles: {', '.join(valid_roles)}")

            elif cmd == "roles":
                print("Agent Roles:")
                print(f"  {'\n'.join(valid_roles)}")

            else:
                print(f"Unknown command '{cmd}'. Type 'help'.")

    @classmethod
    def get(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance