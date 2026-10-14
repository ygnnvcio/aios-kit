#!/usr/bin/env python3
"""Pruebas del kit: guards, token-stop, wiki y scripts de auditoria.

  python3 scripts/test_guards.py

POR QUE EXISTEN
---------------
Un guard que bloquea de mas se termina apagando, y uno que bloquea de menos no se
nota hasta que pasa el error que debia frenar. Estas pruebas fijan las dos
direcciones. Se corren los .sh reales con el payload JSON que manda Claude Code,
no las funciones sueltas: asi tambien se prueba el cableado.

Todo pasa en carpetas temporales: no toca el repo. Compatible con el python3 que
trae macOS (3.9) y el bash 3.2 del sistema.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parent.parent
HOOKS = RAIZ / ".claude" / "hooks"
PY = sys.executable


def correr(cmd, payload, env=None):
    r = subprocess.run(cmd, input=json.dumps(payload), capture_output=True, text=True, timeout=20, env=env)
    return json.loads(r.stdout) if r.stdout.strip() else None


def decision_pre(salida):
    """allow si el guard no dijo nada; si no, deny o ask."""
    if not salida:
        return "allow"
    return salida["hookSpecificOutput"]["permissionDecision"]


def bash(cmd, cwd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}


class GuardOutwardTests(unittest.TestCase):
    def d(self, cmd):
        return decision_pre(correr([str(HOOKS / "guard-outward.sh")], bash(cmd, str(RAIZ))))

    # Lo que tiene que frenar
    def test_merge_pregunta(self):
        self.assertEqual(self.d("gh pr merge 22 --squash"), "ask")

    def test_comentario_pregunta(self):
        self.assertEqual(self.d("gh pr comment 5 -b 'hola'"), "ask")

    def test_crear_pr_pregunta(self):
        self.assertEqual(self.d("gh pr create --title x --body y"), "ask")

    def test_merge_por_api_pregunta(self):
        self.assertEqual(self.d("gh api repos/o/r/pulls/5/merge --method PUT"), "ask")

    def test_comentario_por_api_pregunta(self):
        self.assertEqual(self.d("gh api repos/o/r/issues/3/comments -f body=x"), "ask")

    def test_merge_anidado_en_bash_c_pregunta(self):
        self.assertEqual(self.d('cd /tmp && bash -c "gh pr merge 5"'), "ask")

    def test_invocacion_en_linea_nueva_pregunta(self):
        self.assertEqual(self.d("git status\ngh pr merge 5"), "ask")

    # Lo que tiene que dejar pasar: el falso positivo mata al guard
    def test_lectura_de_pr_pasa(self):
        self.assertEqual(self.d("gh pr view 48 --comments"), "allow")

    def test_lectura_de_comentarios_por_api_pasa(self):
        self.assertEqual(self.d("gh api repos/o/r/issues/3/comments"), "allow")

    def test_mencion_dentro_de_un_string_pasa(self):
        self.assertEqual(self.d("echo 'primero cd /tmp && gh pr comment 5 -b x'"), "allow")

    def test_commit_que_nombra_merge_pasa(self):
        self.assertEqual(self.d('git commit -m "documenta por que gh pr merge pregunta"'), "allow")

    def test_heredoc_con_mencion_pasa(self):
        self.assertEqual(self.d("cat > nota.md <<'EOF'\ngh pr merge solo con permiso\nEOF"), "allow")

    def test_invocacion_despues_del_heredoc_pregunta(self):
        self.assertEqual(self.d("cat > nota.md <<'EOF'\ntexto\nEOF\ngh pr merge 5"), "ask")

    def test_invocacion_entre_parentesis_pregunta(self):
        self.assertEqual(self.d("(gh pr merge 5)"), "ask")

    def test_punto_y_coma_pegado_al_salto_pregunta(self):
        self.assertEqual(self.d("echo a;\ngh pr merge 5"), "ask")

    def test_redireccion_no_parte_el_comando(self):
        self.assertEqual(self.d("gh pr view 5 2>&1 | head"), "allow")


class GuardPlanDecideTests(unittest.TestCase):
    def d(self, plan):
        p = {"tool_name": "ExitPlanMode", "tool_input": {"plan": plan}}
        return decision_pre(correr([str(HOOKS / "guard-plan-decide.sh")], p))

    def test_plan_sin_etiquetas_bloquea(self):
        self.assertEqual(self.d("1. hacer x\n2. hacer y"), "deny")

    def test_plan_de_pura_ejecucion_pasa(self):
        self.assertEqual(self.d("Decide: ninguna\n1. renombrar archivo"), "allow")

    def test_plan_con_las_cuatro_etiquetas_pasa(self):
        plan = ("Decide: proveedor\nOpciones evaluadas: A, B\nVariable que decide: costo (fuente: web)\n"
                "Restricciones declaradas: ninguna")
        self.assertEqual(self.d(plan), "allow")


class _RepoTemporal(unittest.TestCase):
    """Un repo temporal hace de raiz del AIOS (GUARD_AJENO_RAIZ)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "aios")
        os.makedirs(self.repo)

        def g(*a):
            subprocess.run(["git", "-C", self.repo] + list(a), capture_output=True, check=True)
        g("init", "-q")
        g("config", "user.email", "t@t")
        g("config", "user.name", "t")
        for f in ("README.md", "otro.md"):
            Path(self.repo, f).write_text("base\n")
        g("add", ".")
        g("commit", "-qm", "base")
        self.env = dict(os.environ, GUARD_AJENO_RAIZ=self.repo)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class GuardStashTests(_RepoTemporal):
    def d(self, cmd):
        return decision_pre(correr([str(HOOKS / "guard-commit-ajeno.sh")], bash(cmd, self.repo), self.env))

    def test_autostash_frena(self):
        self.assertEqual(self.d("git pull -q --rebase --autostash"), "deny")

    def test_stash_frena(self):
        self.assertEqual(self.d("git stash"), "deny")
        self.assertEqual(self.d("git stash push -m x"), "deny")

    def test_leer_stash_y_merge_pasan(self):
        self.assertEqual(self.d("git stash list"), "allow")
        self.assertEqual(self.d("git fetch -q && git merge origin/main"), "allow")


class GuardCommitAjenoTests(_RepoTemporal):
    PROPIA = "| Fila que escribio esta sesion con un texto suficientemente largo |"
    AJENA = "### Seccion que agrego otra sesion de Claude mientras esta trabajaba"

    def setUp(self):
        super().setUp()
        self.transcript = os.path.join(self.tmp, "sesion.jsonl")
        self.escribir_transcript(self.transcript, "python3 - <<'EOF'\nfila = '" + self.PROPIA + "'\nEOF")

    @staticmethod
    def escribir_transcript(ruta, comando):
        linea = {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": comando}}]}}
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        Path(ruta).write_text(json.dumps(linea, ensure_ascii=False) + "\n")

    def agregar(self, archivo, *lineas):
        with open(os.path.join(self.repo, archivo), "a") as f:
            f.write("".join(l + "\n" for l in lineas))

    def d(self, cmd, transcript="default", cwd=None):
        p = bash(cmd, cwd or self.repo)
        if transcript:
            p["transcript_path"] = self.transcript if transcript == "default" else transcript
        return decision_pre(correr([str(HOOKS / "guard-commit-ajeno.sh")], p, self.env))

    # Lo que tiene que frenar
    def test_linea_de_otra_sesion_frena(self):
        self.agregar("README.md", self.PROPIA, self.AJENA)
        self.assertEqual(self.d('git add README.md && git commit -q -m "x" -- README.md'), "deny")

    def test_solo_ajeno_frena(self):
        self.agregar("README.md", self.AJENA)
        self.assertEqual(self.d('cd "%s" && git add README.md && git commit -m "mio"' % self.repo, cwd=self.tmp), "deny")

    def test_commit_a_frena(self):
        self.agregar("otro.md", self.AJENA)
        self.assertEqual(self.d('git commit -am "x"'), "deny")

    def test_lo_ya_indexado_cuenta(self):
        self.agregar("otro.md", self.AJENA)
        subprocess.run(["git", "-C", self.repo, "add", "otro.md"], check=True)
        self.assertEqual(self.d('git commit -m "x"'), "deny")

    # Lo que tiene que pasar
    def test_solo_lo_propio_indexado_pasa_con_lo_ajeno_en_el_arbol(self):
        """El metodo que el guard recomienda: el archivo desde HEAD con la edicion propia, por update-index."""
        self.agregar("README.md", self.PROPIA, self.AJENA)
        sha = subprocess.run(["git", "-C", self.repo, "hash-object", "-w", "--stdin"], input="base\n" + self.PROPIA + "\n",
                             capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "-C", self.repo, "update-index", "--cacheinfo", "100644,%s,README.md" % sha], check=True)
        self.assertEqual(self.d('git commit -q -m "x"'), "allow")

    def test_linea_propia_pasa(self):
        self.agregar("README.md", self.PROPIA)
        self.assertEqual(self.d('git add README.md && git commit -m "x"'), "allow")

    def test_linea_de_un_subagente_pasa(self):
        sub = os.path.join(self.tmp, "sesion", "subagents", "agent-1.jsonl")
        self.escribir_transcript(sub, "echo '" + self.AJENA + "' >> README.md")
        self.agregar("README.md", self.AJENA)
        self.assertEqual(self.d('git commit -am "x"'), "allow")

    def test_prefijo_ajeno_ok_pasa(self):
        self.agregar("README.md", self.AJENA)
        self.assertEqual(self.d('AJENO_OK=1 git commit -am "indice generado"'), "allow")

    def test_lineas_cortas_no_cuentan(self):
        self.agregar("README.md", "|---|---|", "}")
        self.assertEqual(self.d('git commit -am "x"'), "allow")

    def test_sin_transcript_pasa(self):
        self.agregar("README.md", self.AJENA)
        self.assertEqual(self.d('git commit -am "x"', transcript=None), "allow")

    def test_otro_repo_pasa(self):
        otro = os.path.join(self.tmp, "otro")
        subprocess.run(["git", "init", "-q", otro], check=True)
        Path(otro, "a.md").write_text(self.AJENA + "\n")
        self.assertEqual(self.d('git -C "%s" add a.md && git -C "%s" commit -m x' % (otro, otro)), "allow")


class TokenStopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.transcript = os.path.join(self.tmp, "t.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sesion(self, turnos, ctx):
        with open(self.transcript, "w") as f:
            for _ in range(turnos):
                f.write(json.dumps({"type": "assistant", "message": {"usage": {
                    "input_tokens": 10, "cache_read_input_tokens": ctx, "output_tokens": 100}}}) + "\n")

    def correr(self, *flags):
        # Copia del hook en una raiz temporal: su estado (.claude/tmp) no ensucia el repo.
        hooks = os.path.join(self.tmp, ".claude", "hooks")
        os.makedirs(hooks, exist_ok=True)
        shutil.copy(str(HOOKS / "token-stop.py"), hooks)
        p = {"transcript_path": self.transcript, "session_id": "prueba"}
        return correr([PY, os.path.join(hooks, "token-stop.py")] + list(flags), p)

    def test_sesion_chica_no_dice_nada(self):
        self.sesion(5, 20_000)
        self.assertIsNone(self.correr())

    def test_aviso_por_contexto(self):
        self.sesion(5, 130_000)
        salida = self.correr("--aviso-ctx", "120000", "--stop-ctx", "160000")
        self.assertIn("AVISO DE TOKENS", salida["hookSpecificOutput"]["additionalContext"])

    def test_stop_por_acumulado_deja_la_continuacion(self):
        self.sesion(10, 100_000)  # ~1 M acumulado
        texto = self.correr("--aviso-m", "0.5", "--stop-m", "0.9")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("STOP DE TOKENS", texto)
        self.assertIn("spawn_task", texto)
        self.assertIn("traspaso.md", texto)

    def test_no_repite_el_mismo_nivel(self):
        self.sesion(5, 130_000)
        self.assertIsNotNone(self.correr())
        self.assertIsNone(self.correr())

    def test_transcript_roto_falla_en_silencio(self):
        with open(self.transcript, "w") as f:
            f.write("esto no es json\n")
        self.assertIsNone(self.correr())


class WikiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raiz = os.path.join(self.tmp, "aios")
        shutil.copytree(str(RAIZ / "wiki"), os.path.join(self.raiz, "wiki"),
                        ignore=shutil.ignore_patterns(".manifest.lock", "__pycache__"))
        Path(self.raiz, "wiki", "manifest.json").write_text('{\n  "sources": []\n}\n')
        Path(self.raiz, "wiki", "index.md").write_text("# Indice\n")
        self.wiki = [PY, os.path.join(self.raiz, "wiki", "tools", "wiki.py")]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def w(self, *args):
        return subprocess.run(self.wiki + list(args), capture_output=True, text=True, cwd=self.raiz)

    def test_ciclo_completo(self):
        fuente = Path(self.raiz, "references", "nota.md")
        fuente.parent.mkdir(parents=True)
        fuente.write_text("# Una nota\n")
        self.assertEqual(self.w("capture", str(fuente), "--title", "Nota").returncode, 0)
        pagina = Path(self.raiz, "wiki", "conceptos", "nota.md")
        pagina.write_text("---\ntitle: Nota\ntype: concepto\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
                          "evidence: declaracion\nsources: S01\n---\n\n# Nota\n")
        Path(self.raiz, "wiki", "index.md").write_text("# Indice\n\n- [Nota](conceptos/nota.md)\n")
        self.assertEqual(self.w("integrate", "S01", "--pages", "conceptos/nota.md", "--scope", "entera").returncode, 0)
        r = self.w("check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads(r.stdout)["errors"], [])

    def test_captura_alterada_es_error(self):
        fuente = Path(self.raiz, "nota.md")
        fuente.write_text("original\n")
        self.w("capture", str(fuente))
        snap = next(Path(self.raiz, "raw").rglob("nota.md"))
        snap.chmod(0o644)
        snap.write_text("alterado\n")
        self.assertEqual(self.w("check").returncode, 1)

    def test_wiki_compartida_no_guarda_rutas_personales(self):
        Path(self.raiz, ".wiki-compartida").touch()
        fuera = os.path.join(self.tmp, "privado", "nota.md")
        os.makedirs(os.path.dirname(fuera))
        Path(fuera).write_text("nota\n")
        self.w("capture", fuera)
        manifiesto = Path(self.raiz, "wiki", "manifest.json").read_text()
        self.assertIn("externo:nota.md", manifiesto)
        self.assertNotIn(self.tmp, manifiesto)


class PortabilidadTests(unittest.TestCase):
    """Corre en cualquier Mac: sin rutas absolutas de nadie y sin opciones de GNU."""
    ARCHIVOS = [p for p in list(HOOKS.glob("*")) + list((RAIZ / "scripts").glob("*")) +
                list((RAIZ / ".claude" / "skills").rglob("*.py")) + [RAIZ / "wiki" / "tools" / "wiki.py"]
                if p.is_file() and p.suffix in (".py", ".sh")]

    def test_sin_rutas_de_usuario(self):
        for p in self.ARCHIVOS:
            self.assertNotRegex(p.read_text(), r"/Users/[a-z]|/home/[a-z]", p.name)

    def test_ejecutables(self):
        for p in self.ARCHIVOS:
            self.assertTrue(os.access(str(p), os.X_OK), "%s no es ejecutable (chmod +x)" % p.name)

    def test_sin_opciones_gnu(self):
        for p in self.ARCHIVOS:
            if p.suffix == ".sh":
                texto = p.read_text()
                self.assertNotIn("sed -i ", texto.replace("sed -i ''", ""), p.name)
                self.assertNotIn("stat -c", texto, p.name)
                self.assertIsNone(re.search(r"declare -A|mapfile|readarray", texto), p.name)

    def test_python_compila(self):
        for p in self.ARCHIVOS:
            if p.suffix == ".py":
                compile(p.read_text(), str(p), "exec")

    def test_scripts_responden_help(self):
        for s in ("frescura.py", "estado_git.py", "revisar.py"):
            r = subprocess.run([PY, str(RAIZ / "scripts" / s), "--help"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, s + r.stderr)

    def test_settings_de_ejemplo_apunta_a_hooks_reales(self):
        ejemplo = RAIZ / ".claude" / "settings.example.json"
        if not ejemplo.exists():
            self.skipTest("settings.example.json no esta en esta raiz")
        texto = ejemplo.read_text()
        json.loads(texto)
        for ruta in re.findall(r"\.claude/hooks/([\w.-]+)", texto):
            self.assertTrue((HOOKS / ruta).exists(), ruta)


if __name__ == "__main__":
    unittest.main(verbosity=1)
