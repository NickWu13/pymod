"""Fabric Java Mod generator (stage 5).

Emits a standard Fabric Loom Gradle project that builds against the *real*
26.2 dependency set from the game profile (loader, fabric-api, official
mappings -- Yarn has no 26.2 build).  Tags become resource-pack JSON files
(zero API risk); item/block registrations become Java ``Registry.register``
calls whose exact 26.2 signatures are validated by compiling the generated
project (see the build loop in ``docs/targets.md``).  Events/actions are gated
out by the capability matrix until each mapping is proven to compile.
"""
from __future__ import annotations

import json
from pathlib import Path

from ...errors import TargetError
from ...ir.irnodes import ModSpec
from ...registry.gameprofile import profile_for
from ..base import CodeTarget
from . import templates as T

_VANILLA_TAG_CATEGORIES = ("items", "blocks", "functions", "entity_types")


class FabricTarget(CodeTarget):
    name = "fabric"

    def __init__(self, spec: ModSpec, out_dir: Path, game_version: str = "26.2") -> None:
        super().__init__(spec, out_dir)
        self.game_version = game_version
        self.profile = profile_for(game_version)

    # ------------------------------------------------------------------
    def generate(self) -> list[Path]:
        written: list[Path] = []
        modid = self.spec.info.id
        java_release = self.profile.java_version or "21"

        written.append(self.write("settings.gradle.kts", T.settings_gradle(self.profile)))
        written.append(
            self.write(
                "build.gradle.kts",
                T.build_gradle(self.profile, modid, self.spec.info.version, java_release),
            )
        )
        written.append(self.write("gradle.properties", T.gradle_properties()))
        written.append(
            self.write(
                "gradle/wrapper/gradle-wrapper.properties", T.wrapper_properties(self.profile)
            )
        )
        written.append(self.write("mappings/identity.tiny", T.identity_mappings()))

        entrypoint = T.entrypoint_main(modid, self.spec.info.name, self._java_regs())
        cls = T.main_class_name(modid)
        written.append(
            self.write(
                f"src/main/java/{T.package_name(modid).replace('.', '/')}/{cls}.java", entrypoint
            )
        )
        written.append(
            self.write(
                "src/main/resources/fabric.mod.json",
                T.fabric_mod_json(
                    self.profile, modid, self.spec.info.name, self.spec.info.version,
                    self.spec.info.description, f"{T.package_name(modid)}.{cls}",
                ),
            )
        )

        for reg in self.spec.registrations:
            if reg.kind == "tag":
                written.append(self._emit_tag_resource(reg))

        return written

    # ------------------------------------------------------------------
    def _java_regs(self) -> list[tuple[str, str, dict]]:
        """item/block registrations that become Java code (tags are resources)."""
        out: list[tuple[str, str, dict]] = []
        for reg in self.spec.registrations:
            if reg.kind in ("item", "block"):
                out.append((reg.kind, reg.name, dict(reg.props)))
        return out

    def _emit_tag_resource(self, reg) -> Path:
        modid = self.spec.info.id
        name = reg.name
        if "/" in name:
            category, _, base = name.rpartition("/")
        else:
            category, base = "items", name
        if category not in _VANILLA_TAG_CATEGORIES:
            raise TargetError(
                "bad-tag-category",
                f"fabric tag {reg.name!r} uses unknown category {category!r}; "
                "use items/... or blocks/...",
                loc=reg.loc,
            )
        doc = {"replace": False, "values": list(dict(reg.props).get("values", ()))}
        rel = f"src/main/resources/data/{modid}/tags/{category}/{base}.json"
        return self.write(rel, json.dumps(doc, indent=2))