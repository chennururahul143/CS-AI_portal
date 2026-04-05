MODULES = [
    {
        "code": "CS603",
        "name": "Rigorous Software Process",
        "topics": [
            "Agile methodologies, Scrum, Kanban, XP",
            "Waterfall and spiral models",
            "CI/CD pipelines and DevOps",
            "Version control with Git",
            "CMMI process improvement",
            "Sprint planning, backlog, retrospectives",
            "Software lifecycle management",
            "Lean and continuous delivery"
        ]
    },
    {
        "code": "CS605",
        "name": "Mathematics and Theory of Computer Science",
        "topics": [
            "Finite automata, DFA, NFA",
            "Formal languages and grammars",
            "Chomsky hierarchy",
            "Turing machines and computability",
            "Decidability and the halting problem",
            "Computational complexity, P vs NP",
            "Big-O notation and asymptotic analysis",
            "Set theory, logic, and proofs",
            "Graph theory and discrete mathematics"
        ]
    },
    {
        "code": "CS607",
        "name": "Requirements Engineering and System Design",
        "topics": [
            "Requirements elicitation and validation",
            "Functional and non-functional requirements",
            "Use cases and user stories",
            "UML diagrams: class, sequence, use case",
            "Software architecture patterns",
            "SOLID principles",
            "MVC, microservices, monolithic architecture",
            "API design and system specifications",
            "Stakeholder analysis"
        ]
    },
    {
        "code": "CS608",
        "name": "Software Testing",
        "topics": [
            "Unit testing, integration testing, system testing",
            "Black box and white box testing",
            "Test-driven development (TDD)",
            "Behaviour-driven development (BDD)",
            "Test coverage: statement, branch, path",
            "Equivalence partitioning and boundary value analysis",
            "Regression testing and smoke testing",
            "Test automation with Selenium, pytest, JUnit",
            "Mutation testing and mock objects"
        ]
    },
    {
        "code": "CS610",
        "name": "Interaction Design",
        "topics": [
            "User-centred design principles",
            "Usability heuristics (Nielsen)",
            "Wireframing and prototyping",
            "User research and personas",
            "Journey mapping",
            "Accessibility and WCAG standards",
            "Gestalt principles",
            "Affordance and mental models",
            "Figma and design tools",
            "A/B testing and user testing"
        ]
    },
    {
        "code": "CS613",
        "name": "Advanced Concepts in OOP",
        "topics": [
            "Encapsulation, inheritance, polymorphism, abstraction",
            "SOLID principles in depth",
            "Creational patterns: Factory, Singleton, Builder",
            "Structural patterns: Adapter, Facade, Composite",
            "Behavioural patterns: Observer, Strategy, Command",
            "Dependency injection and inversion of control",
            "Coupling, cohesion, and clean code",
            "Liskov substitution principle",
            "Interface segregation and open/closed principle"
        ]
    },
    {
        "code": "CS616",
        "name": "Practical Cryptography",
        "topics": [
            "Symmetric encryption: AES, DES",
            "Asymmetric encryption: RSA, ECC",
            "Hash functions: SHA-256, MD5",
            "Digital signatures and certificates",
            "Public key infrastructure (PKI)",
            "SSL/TLS protocols",
            "Diffie-Hellman key exchange",
            "Message authentication codes (MAC, HMAC)",
            "Block and stream ciphers",
            "Post-quantum cryptography basics"
        ]
    },
    {
        "code": "CS618",
        "name": "Deep Learning for Software Engineers",
        "topics": [
            "Neural network fundamentals",
            "Backpropagation and gradient descent",
            "Convolutional Neural Networks (CNN)",
            "Recurrent Neural Networks (RNN, LSTM)",
            "Transformer architecture and attention",
            "Large Language Models (LLMs), GPT, BERT",
            "PyTorch and TensorFlow",
            "Overfitting, dropout, batch normalisation",
            "Transfer learning and fine-tuning",
            "NLP tasks: classification, generation"
        ]
    }
]

def build_modules_context():
    lines = ["KNOWLEDGE BASE — 8 Masters CS Modules:\n"]
    for m in MODULES:
        lines.append(f"{m['code']} — {m['name']}:")
        for t in m["topics"]:
            lines.append(f"  • {t}")
        lines.append("")
    return "\n".join(lines)

MODULES_CONTEXT = build_modules_context()