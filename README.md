# Unity Scripting Crawler

Crawls [Unity Scripting Reference](http://docs.unity3d.com/Documentation/ScriptReference/index.html)
to index class variables and functions.

One use of this data is the generation of [Unity Completions](https://github.com/oferei/sublime-unity-completions),
a plugin for Sublime Text 2 which provides auto-completion.

The output file unity.pkl is included for convenience.

## Output Format

Output file is a pickle with the following hierarchy:

* Dictionary by section (e.g., "Runtime Classes", "Runtime Attributes")
* Dictionary by class name
* Dictionary by class member name
* List of definitions (for functions) or None (for variables)
* Function definition is a dictionary with the following keys:
	1. "template" - Template postfix if relevant (e.g. ".<T>") or None
	* "params" - List of function parameters, which are dictionaries with the following keys:
		1. "name" - Name of parameter
		* "type" - Type of parameter
		* "default" - Default value or None
	* "returnType" - Return type

## Retrieved Sections

The following sections are retrieved:

* [Runtime Classes](http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.html)
 * [Attributes](http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Attributes.html)
 * [Enumerations](http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Enumerations.html)
* [Editor Classes](http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Editor_Classes.html)
 * [Attributes](http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Editor_Attributes.html)
 * [Enumerations](http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Editor_Enumerations.html)
