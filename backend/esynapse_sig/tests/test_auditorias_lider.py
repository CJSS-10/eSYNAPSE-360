"""
M10 Auditorías: el auditor líder tiene una sola fuente, el equipo auditor.

Reglas:
- Solo un integrante con rol líder; un segundo se rechaza.
- El líder puede ser interno o externo; el plan, las actas y el informe
  muestran ese nombre (no otro campo).
- Sin líder en el equipo no se aprueba el plan.
- El campo auditor líder de la auditoría no se edita directamente: refleja
  al líder interno del equipo y queda vacío si el líder es externo.
"""
from esynapse_sig.models import Auditoria

from .test_auditorias import BaseAuditoria


class PruebasLiderUnico(BaseAuditoria):

    def _post(self, accion, datos=None):
        return self.client.post(f'/api/auditorias/{self.aud.pk}/{accion}/', datos or {}, format='json')

    def _plan_listo(self):
        self.client.patch(f'/api/auditorias/{self.aud.pk}/',
                          {'objetivo': 'Evaluar el SIG', 'alcance': 'Todos los procesos',
                           'cronograma_entrevistas': [{'fecha': '2026-05-12', 'area': 'Logística'}]}, format='json')

    def test_un_solo_lider(self):
        r = self._post('agregar_integrante', {'rol': 'lider', 'nombre_externo': 'Óscar', 'cargo': 'Auditor externo'})
        self.assertEqual(r.status_code, 200, r.data)
        r = self._post('agregar_integrante', {'rol': 'lider', 'usuario': self.lider.pk})
        self.assertEqual(r.status_code, 400, 'no se admite un segundo líder')
        self.assertIn('Óscar', str(r.data))

    def test_lider_externo_figura_y_permite_planificar(self):
        self._plan_listo()
        self._post('agregar_integrante', {'rol': 'lider', 'nombre_externo': 'Óscar'})
        self.aud.refresh_from_db()
        self.assertIsNone(self.aud.auditor_lider, 'un líder externo no ocupa el campo de usuario')
        self.assertEqual(self.aud.nombre_lider(), 'Óscar')
        r = self.client.get(f'/api/auditorias/{self.aud.pk}/')
        self.assertEqual(r.data['auditor_lider_nombre'], 'Óscar')
        r = self._post('planificar')
        self.assertEqual(r.status_code, 200, r.data)

    def test_sin_lider_en_equipo_no_se_planifica(self):
        self._plan_listo()
        self._post('agregar_integrante', {'rol': 'auditor', 'nombre_externo': 'Óscar', 'cargo': 'Auditor líder'})
        r = self._post('planificar')
        self.assertEqual(r.status_code, 400, 'un "auditor" con cargo de líder no es el líder')
        self.assertIn('Equipo auditor', str(r.data))

    def test_quitar_al_lider_vacia_el_campo(self):
        self._post('agregar_integrante', {'rol': 'lider', 'usuario': self.lider.pk})
        self.aud.refresh_from_db()
        self.assertEqual(self.aud.auditor_lider, self.lider)
        ig = self.aud.equipo.get(rol='lider')
        self._post('quitar_integrante', {'integrante_id': ig.pk})
        self.aud.refresh_from_db()
        self.assertIsNone(self.aud.auditor_lider)
        self.assertEqual(self.aud.nombre_lider(), '')

    def test_el_campo_lider_no_se_edita_directamente(self):
        r = self.client.patch(f'/api/auditorias/{self.aud.pk}/', {'auditor_lider': self.auditor.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.aud.refresh_from_db()
        self.assertIsNone(self.aud.auditor_lider, 'se ignora: el líder se define en el equipo')

    def test_registro_anterior_pasa_al_equipo_al_planificar(self):
        """Una auditoría con el campo de líder pero sin líder en el equipo
        (registros anteriores) lo incorpora al equipo al aprobar el plan."""
        self._plan_listo()
        Auditoria.objects.filter(pk=self.aud.pk).update(auditor_lider=self.auditor)
        r = self._post('planificar')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.aud.equipo.get(rol='lider').usuario, self.auditor)
