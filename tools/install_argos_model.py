"""Rode uma vez (com internet) para habilitar a tradução offline EN -> PT.
Requer: pip install argostranslate"""
import argostranslate.package as package

package.update_package_index()
pkg = next(p for p in package.get_available_packages() if p.from_code == "en" and p.to_code == "pt")
package.install_from_path(pkg.download())
print("Modelo EN->PT instalado.")
