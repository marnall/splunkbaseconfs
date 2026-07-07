#Intersection Function to compare 2 lists
def intersection(x, y, case_sensitive, delim):
    try:
        #check if provided variables are strings, 
        #check if variable is an empty string,
        #parse by delimiter or convert to list
        if (isinstance(x, str)):
            if x:
                if delim == None:
                    x = [x]
                else:
                    x = list(x.split(delim))
            else:
                x = []

        if (isinstance(y, str)):
            if y:
                if delim == None:
                    y = [y]
                else:
                    y = list(y.split(delim))
            else:
                y = []

        #find intersections based on value of case sensitivity, default=False
        if (case_sensitive == True):  # case sensitive
            x = set(x)
            y = set(y)

            intersect = list(x & y)
            left = list(x - y)
            right = list(y - x)

        else:  # case insensitive
            insensitive_x = set(map(str.casefold, x))
            insensitive_y = set(map(str.casefold, y))

            intersect = list(insensitive_x & insensitive_y)
            left = list(insensitive_x - insensitive_y)
            right = list(insensitive_y - insensitive_x)

        #find final counts and return data
        intersect_count = len(intersect)
        left_count = len(left)
        right_count = len(right)

        relationship = False

        if intersect_count > 0:
            relationship = True
            relationship_status = "Intersecting values found."
        elif not x and not y:
            relationship_status = "All compared fields are NULL."
        elif not x and y:
            relationship_status = "mv_left is NULL."
        elif not y and x:
            relationship_status = "mv_right is NULL."
        else:
            relationship_status = "There are no intersecting values."

        return intersect, intersect_count, left, left_count, right, right_count, relationship, relationship_status

    except TypeError:
        print("Execution failed to find intersect, this appears likely to be due to unsupported field syntax.")