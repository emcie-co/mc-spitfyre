import ast
from collections import defaultdict
import os
import sys
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class AbstractMethod:
    name: str
    module: str
    class_name: str
    lineno: int


@dataclass
class OverrideMethod:
    name: str
    module: str
    class_name: str
    lineno: int
    has_override: bool
    source_file: str


class AbstractMethodFinder(ast.NodeVisitor):
    """Finds all methods marked with @abstractmethod"""

    def __init__(self):
        self.abstract_methods: List[AbstractMethod] = []
        self.current_class = None
        self.current_module = None

    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check if method has @abstractmethod decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                assert self.current_module and self.current_class
                self.abstract_methods.append(
                    AbstractMethod(
                        name=node.name,
                        module=self.current_module,
                        class_name=self.current_class,
                        lineno=node.lineno,
                    )
                )

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Check if method has @abstractmethod decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                assert self.current_module and self.current_class
                self.abstract_methods.append(
                    AbstractMethod(
                        name=node.name,
                        module=self.current_module,
                        class_name=self.current_class,
                        lineno=node.lineno,
                    )
                )


class ImplementationFinder(ast.NodeVisitor):
    """Finds concrete implementations of abstract methods"""

    def __init__(self, abstract_methods: List[AbstractMethod]):
        self.abstract_method_names = {method.name for method in abstract_methods}
        self.abstract_classes = {method.class_name for method in abstract_methods}
        self.implementations: List[OverrideMethod] = []
        self.current_class = None
        self.current_module = None
        self.inheritance_map: Dict[str, Set[str]] = {}

    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name

        # Store inheritance information
        bases = {
            base.id if isinstance(base, ast.Name) else base.attr
            for base in node.bases
            if isinstance(base, (ast.Name, ast.Attribute))
        }
        self.inheritance_map[node.name] = bases

        # Only look for implementations in non-abstract classes
        if self.current_class not in self.abstract_classes:
            self.generic_visit(node)

        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Only process methods that match abstract method names
        if node.name in self.abstract_method_names:
            has_override = any(
                isinstance(d, ast.Name) and d.id == "override" for d in node.decorator_list
            )
            # Make sure this isn't the abstract method itself
            if not any(
                isinstance(d, ast.Name) and d.id in ["abstractmethod", "staticmethod"]
                for d in node.decorator_list
            ):
                assert self.current_module and self.current_class
                self.implementations.append(
                    OverrideMethod(
                        name=node.name,
                        module=self.current_module,
                        class_name=self.current_class,
                        lineno=node.lineno,
                        has_override=has_override,
                        source_file=self.current_file,
                    )
                )

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Only process methods that match abstract method names
        if node.name in self.abstract_method_names:
            has_override = any(
                isinstance(d, ast.Name) and d.id == "override" for d in node.decorator_list
            )
            # Make sure this isn't the abstract method itself
            if not any(
                isinstance(d, ast.Name) and d.id == "abstractmethod" for d in node.decorator_list
            ):
                self.implementations.append(
                    OverrideMethod(
                        name=node.name,
                        module=self.current_module,
                        class_name=self.current_class,
                        lineno=node.lineno,
                        has_override=has_override,
                        source_file=self.current_file,
                    )
                )


def add_override_decorator(file_path: str, line_number: int) -> None:
    """Add @override decorator to a concrete implementation."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find the method definition line
    method_line = lines[line_number - 1]

    indent = len(method_line) - len(method_line.lstrip())

    # Insert @override decorator with proper indentation
    decorator_line = " " * indent + "@override\n"
    target_line = lines[line_number - 2]
    while "@" in target_line and "@property" not in target_line:
        line_number -= 1
        target_line = lines[line_number - 2]

    lines.insert(line_number - 1, decorator_line)

    # Write back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def process_codebase(directory: str) -> Tuple[List[AbstractMethod], List[OverrideMethod]]:
    """Process the codebase to find abstract methods and their implementations."""
    # First pass: find all abstract methods
    abstract_methods = []
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                finder = AbstractMethodFinder()
                finder.current_module = file_path
                finder.visit(tree)
                abstract_methods.extend(finder.abstract_methods)

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    # Second pass: find implementations
    implementations = []
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                finder = ImplementationFinder(abstract_methods)
                finder.current_module = file_path
                finder.current_file = file_path
                finder.visit(tree)
                implementations.extend(finder.implementations)

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    return abstract_methods, implementations


def main(directory: str, auto_fix: bool = False, dry_run: bool = False):
    """Main function to analyze and optionally fix missing @override decorators."""
    print("Analyzing codebase...")
    abstract_methods, implementations = process_codebase(directory)

    print("\nAbstract Methods Found:")
    for method in abstract_methods:
        print(f"- {method.class_name}.{method.name} in {method.module}:{method.lineno}")

    print("\nImplementations Found:")
    missing_overrides = []
    for impl in implementations:
        status = "has @override" if impl.has_override else "missing @override"
        print(f"- {impl.class_name}.{impl.name} in {impl.source_file}:{impl.lineno} ({status})")
        if not impl.has_override:
            missing_overrides.append(impl)

    if missing_overrides:
        if dry_run:
            print("\nChanges that would be made:")
            for impl in missing_overrides:
                print(
                    f"Would add @override to {impl.class_name}.{impl.name} in {impl.source_file}:{impl.lineno}"
                )
        elif auto_fix:
            offsets: defaultdict[str, int] = defaultdict(lambda: 0)
            print("\nAdding missing @override decorators...")
            for impl in missing_overrides:
                try:
                    offset = offsets[impl.source_file]
                    add_override_decorator(impl.source_file, impl.lineno + offset)
                    offsets[impl.source_file] += 1
                    print(f"Added @override to {impl.class_name}.{impl.name}")
                except Exception as e:
                    print(f"Error adding @override to {impl.class_name}.{impl.name}: {e}")


if __name__ == "__main__":
    path = "src"
    if len(sys.argv) >= 2:
        path = sys.argv[1]
    main(path, auto_fix=True)
