from sismic.interpreter import Interpreter
from sismic.io import import_from_yaml
from sismic.model import Event

class CounterEvaluator:
    def __init__(self, limit=3):
        self.count = 0
        self.limit = limit
    
    def is_limit_reached(self, event):
        """Guard function that checks if counter reached limit"""
        self.count += 1
        print("called")
        return self.count >= self.limit

def main():
    # Load the YAML statechart
    with open('statechart.yaml') as f:
        statechart = import_from_yaml(f)
    
    # Create evaluator and interpreter
    evaluator = CounterEvaluator(limit=3)
    interpreter = Interpreter(
        statechart,
        initial_context={'is_limit_reached': evaluator.is_limit_reached}
    )
    
    # Execute until done
    interpreter.queue(Event('increment'))
    steps = interpreter.execute()
    print(steps)
    print(f"Current state: {interpreter.configuration}")
        
if __name__ == '__main__':
    main()