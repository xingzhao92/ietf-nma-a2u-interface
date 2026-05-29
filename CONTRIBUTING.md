# Contributing to NMA A2U Framework Draft

Thank you for your interest in contributing to this IETF draft!

## How to Contribute

### Reporting Issues

- Use [GitHub Issues](../../issues) to report bugs or propose enhancements
- For IETF process-related discussions, use the [NMOP WG mailing list](mailto:nmop@ietf.org)

### Proposing Changes

1. **Fork** this repository
2. **Create a branch** for your changes (`git checkout -b feature/your-feature`)
3. **Make changes** to the XML draft or YANG modules
4. **Validate** your changes locally:
   ```bash
   make validate      # Validate XML
   make validate-yang # Validate YANG modules
   make all           # Generate outputs
   ```
5. **Submit a Pull Request** with a clear description of changes

### YANG Model Changes

When modifying YANG modules:

- Follow [RFC 8407](https://www.rfc-editor.org/rfc/rfc8407.html) (YANG Guidelines)
- Run `pyang --ietf` validation before submitting
- Ensure backward compatibility when possible
- Update the `revision` statement with date and description
- Update the XML draft to reflect YANG changes

### Draft Text Changes

When modifying the draft XML:

- Ensure all `<xref>` references resolve correctly
- Maintain consistent terminology (see Terminology section in draft)
- Follow IETF style guidelines for RFC 2119 keywords
- Run `xml2rfc --v3` to validate structure

### Version Numbering

- This repository tracks **-00** version of the draft
- Subsequent versions will be managed through IETF datatracker
- Git tags will be used to mark milestone versions

## Discussion

- **Technical discussions**: [NMOP WG mailing list](https://www.ietf.org/mailman/listinfo/nmop)
- **GitHub-specific issues**: Use this repository's issue tracker

## Code of Conduct

This project follows the IETF's [Note Well](https://www.ietf.org/about/note-well/) policy for open participation.
