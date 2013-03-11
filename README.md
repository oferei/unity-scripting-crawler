# Unity Scripting Crawler

Crawls [Unity Scripting Reference](http://docs.unity3d.com/Documentation/ScriptReference/index.html)
to index class variables and functions.

One possible use for this data is the creation of a plugin for Sublime Text which would provide auto-completion.

Retrieved sections:
* Runtime Classes
 * Attributes
 * Enumerations
* Editor Classes
 * Attributes
 * Enumerations

The output file unity.pkl is included for convenience.

## Output Format

Output file is a pickle with the following hierarchy:

* Dictionary by section (e.g., "Runtime Classes", "Runtime Attributes")
* Dictionary by class name
* Dictionary by class member name
* list of definitions (for functions) or None (for variables)
* Function definition is a dictionary with the following keys:
	1. "template" - Template postfix if relevant (e.g. ".<T>") or None
	* "params" - List of function parameters, which are dictionaries with the following keys:
		1. "name" - Name of parameter
		* "type" - Type of parameter
		* "default" - Default value or None
	* "returnType" - Return type
