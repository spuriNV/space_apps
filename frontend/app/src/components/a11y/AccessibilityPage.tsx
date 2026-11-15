import { Dialog } from './Dialog';
import { DisabilityHelp } from '../help/DisabilityHelp';
import { t } from '../../i18n';

/** What CropLytics supports for access, and how it was checked. Linked from the menu and the footer of the Pick panel. */
export function AccessibilityPage({ onClose }: { onClose: () => void }) {
  return (
    <Dialog title={t('ui.a11y')} onClose={onClose} testid="a11y-page">
      <p>{t('ui.a11y.p1')}</p>
      <h3>{t('ui.a11y.h1')}</h3>
      <ul>
        <li><b>{t('ui.a11y.s1b')}</b> {t('ui.a11y.s1')}</li>
        <li><b>{t('ui.a11y.s2b')}</b> {t('ui.a11y.s2')}</li>
        <li><b>{t('ui.a11y.s3b')}</b> {t('ui.a11y.s3')}</li>
        <li><b>{t('ui.a11y.s4b')}</b> {t('ui.a11y.s4')}</li>
        <li><b>{t('ui.a11y.s5b')}</b> {t('ui.a11y.s5')}</li>
        <li><b>{t('ui.a11y.s6b')}</b> {t('ui.a11y.s6')}</li>
        <li><b>{t('ui.a11y.s7b')}</b> {t('ui.a11y.s7')}</li>
        <li><b>{t('ui.a11y.s8b')}</b> {t('ui.a11y.s8')}</li>
        <li><b>{t('ui.a11y.s9b')}</b> {t('ui.a11y.s9')}</li>
      </ul>
      <h3>{t('merge.readAloud')}</h3>
      <p>{t('merge.readAloudP')}</p>
      <DisabilityHelp />
      <h3>{t('ui.a11y.h2')}</h3>
      <ul>
        <li>{t('ui.a11y.t1')}</li>
        <li>{t('ui.a11y.t2')}</li>
        <li>{t('ui.a11y.t3')}</li>
        <li>{t('ui.a11y.t4')}</li>
      </ul>
    </Dialog>
  );
}
