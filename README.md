# About
This project is focused on creating JSON files that define objects used in
Minecraft Bedrock Edition resource- and behavior-packs. The goal of this
project is to enable an easy way of generating code for tool used to
edit or analyse the packs.

Every object definition describes how to obtain following information about the
object:
- name of the class of the object (defined by the json file name)
- classification: behavior- or resource-pack object
- glob file path pattern relative to owning pack to access the file with the
    object
- does the file define one or many objects of this type
- JSON path to data of this object
- How to get the identifier of the object
    - from file path (if that's how the object defines its identifier)
    - from data at certain JSON path (relative to JSON path of the object)
    - additional information about postprocessing that needs to be applied to
      the value to retrieve the identifier
- How to get references to other objects (JSON path relative to JSON path of
  the object)

The definitions don't specify the schemas of the JSON files used in
Minecraft packs - only the basic information about their identifiers and
relations between them is included.

# Project structure
- 📁📝 `models/*` - the definitions of the objects
- 📝 `model_file_schema.json` - the JSON schema for files in `models/`
- 📝 `README.md` - this file
