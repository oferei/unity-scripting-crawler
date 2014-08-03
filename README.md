# Unity Scripting Crawler

Crawls [Unity Scripting Reference](http://docs.unity3d.com/Documentation/ScriptReference)
to index class variables and functions.

One use of this data is the generation of [Unity Completions](https://github.com/oferei/sublime-unity-completions),
a plugin for Sublime Text which provides auto-completion.

The output file _unity.pkl_ is included for convenience.

## Output Format

Output file is a pickle with the following hierarchy:

* Dictionary by section (e.g., "Runtime Classes", "Runtime Attributes")
	* Dictionary by class name
		* Dictionary by class member name
			* List of definitions (for functions) or None (for variables).  
			Function definition is a dictionary with the following keys:
				1. "template" - Template postfix if relevant (e.g. ".<T>") or None
				* "params" - List of function parameters, which are dictionaries with the following keys:
					1. "name" - Name of parameter
					* "type" - Type of parameter
					* "default" - Default value or None
				* "returnType" - Return type

## Retrieved Sections

The following sections are retrieved:

* UnityEngine
* UnityEditor
* Other
