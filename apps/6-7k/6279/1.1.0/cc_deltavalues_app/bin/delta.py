
class deltas:


    def __init__(self, current, previous):
        # Initialize & convert data type to set for comparing
        self.current = set(current)
        self.previous = set(previous)


    def get_delta_count(self):
        try:
            # Calculate record counts
            current_count = len(self.current)
            past_count = len(self.previous)

            # Calculate deltas
            delta_count = current_count - past_count
            
        except TypeError:
            print("Execution failed to find delta count, this appears likely to be due to unsupported field syntax.")

        return delta_count


    def get_delta_values(self):
        try:
            # Calculate changes
            add = list(self.current - self.previous)
            remove = list(self.previous - self.current)

            # Add identifier to list output
            for i, e in enumerate(add):
                add[i] = f"(A) {e}"

            for i, e in enumerate(remove):
                remove[i] = f"(R) {e}"

            delta_values = add + remove
            delta_values.sort()

        except TypeError:
            print("Execution failed to find delta values, this appears likely to be due to unsupported field syntax.")

        return delta_values