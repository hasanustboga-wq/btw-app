import React, { useState, useRef, useMemo } from 'react';
import { Upload, FileText, Percent, Loader2, AlertCircle, CheckCircle2, Calculator, Receipt, Trash2, Plus, FileImage, ChevronDown, ChevronUp, ShieldAlert, Globe, FileWarning, Settings2, Table } from 'lucide-react';
import { analyzeInvoice, AnalysisResult } from './lib/gemini';

type InvoiceStatus = 'idle' | 'analyzing' | 'success' | 'error';
type InvoiceTypeOption = 'Automatisch' | 'Aankoop' | 'Verkoop';

interface InvoiceItem {
  id: string;
  file?: File;
  text?: string;
  status: InvoiceStatus;
  result?: AnalysisResult;
  error?: string;
  expanded: boolean;
}

export default function App() {
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [textInput, setTextInput] = useState('');
  const [globalDeduction, setGlobalDeduction] = useState<number>(100);
  const [globalInvoiceType, setGlobalInvoiceType] = useState<InvoiceTypeOption>('Automatisch');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const addFiles = (files: File[]) => {
    const newInvoices = files.map(file => ({
      id: Math.random().toString(36).substring(2, 9),
      file,
      status: 'idle' as InvoiceStatus,
      expanded: true
    }));
    setInvoices(prev => [...prev, ...newInvoices]);
  };

  const handleAddTextInvoice = () => {
    if (!textInput.trim()) return;
    setInvoices(prev => [...prev, {
      id: Math.random().toString(36).substring(2, 9),
      text: textInput.trim(),
      status: 'idle',
      expanded: true
    }]);
    setTextInput('');
  };

  const removeInvoice = (id: string) => {
    setInvoices(prev => prev.filter(inv => inv.id !== id));
  };

  const toggleExpand = (id: string) => {
    setInvoices(prev => prev.map(inv => inv.id === id ? { ...inv, expanded: !inv.expanded } : inv));
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          const base64 = reader.result.split(',')[1];
          resolve(base64);
        } else {
          reject(new Error('Failed to convert file to base64'));
        }
      };
      reader.onerror = error => reject(error);
    });
  };

  const handleAnalyzeAll = async () => {
    const toAnalyze = invoices.filter(inv => inv.status === 'idle' || inv.status === 'error');
    if (toAnalyze.length === 0) return;

    // Mark as analyzing
    setInvoices(prev => prev.map(inv => 
      toAnalyze.some(t => t.id === inv.id) ? { ...inv, status: 'analyzing', error: undefined } : inv
    ));

    // Process concurrently for speed
    await Promise.all(toAnalyze.map(async (inv) => {
      try {
        let content: { fileBase64?: string; mimeType?: string; text?: string } = {};

        if (inv.file) {
          const base64 = await fileToBase64(inv.file);
          content = { fileBase64: base64, mimeType: inv.file.type };
        } else if (inv.text) {
          content = { text: inv.text };
        }

        const result = await analyzeInvoice(content, globalDeduction, globalInvoiceType);
        setInvoices(prev => prev.map(p => p.id === inv.id ? { ...p, status: 'success', result } : p));
      } catch (err: any) {
        console.error(err);
        setInvoices(prev => prev.map(p => p.id === inv.id ? { ...p, status: 'error', error: err.message || 'Fout bij analyse' } : p));
      }
    }));
  };

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return '€ 0.00';
    return new Intl.NumberFormat('nl-BE', { style: 'currency', currency: 'EUR' }).format(value);
  };

  const renderRoosterSection = (title: string, roosters: Record<string, number> | undefined) => {
    if (!roosters) return null;
    const entries = Object.entries(roosters).filter(([_, value]) => value !== undefined && value !== null && value !== 0);
    if (entries.length === 0) return null;

    return (
      <div className="mb-4">
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">{title}</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {entries.map(([rooster, value]) => (
            <div key={rooster} className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                  {rooster}
                </div>
              </div>
              <span className="text-sm font-semibold text-slate-900">{formatCurrency(value)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const pendingCount = invoices.filter(i => i.status === 'idle' || i.status === 'error').length;
  const isAnalyzingAny = invoices.some(i => i.status === 'analyzing');

  // Calculate summary
  const summary = useMemo(() => {
    const totals: Record<string, number> = {};
    
    invoices.forEach(inv => {
      if (inv.status === 'success' && inv.result?.btw_aangifte_roosters) {
        const roosters = [
          ...(inv.result.btw_aangifte_roosters.uitgaande_handelingen_basis ? Object.entries(inv.result.btw_aangifte_roosters.uitgaande_handelingen_basis) : []),
          ...(inv.result.btw_aangifte_roosters.inkomende_handelingen_basis ? Object.entries(inv.result.btw_aangifte_roosters.inkomende_handelingen_basis) : []),
          ...(inv.result.btw_aangifte_roosters.verschuldigde_belasting ? Object.entries(inv.result.btw_aangifte_roosters.verschuldigde_belasting) : []),
          ...(inv.result.btw_aangifte_roosters.aftrekbare_belasting ? Object.entries(inv.result.btw_aangifte_roosters.aftrekbare_belasting) : [])
        ];

        roosters.forEach(([code, value]) => {
          if (value) {
            totals[code] = (totals[code] || 0) + value;
          }
        });
      }
    });

    return totals;
  }, [invoices]);

  const hasSummary = Object.keys(summary).length > 0;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-blue-200 pb-20">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <header className="mb-10 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 text-white mb-6 shadow-lg shadow-blue-600/20">
            <Receipt className="w-8 h-8" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 mb-3">Belgische Btw-assistent (Batch)</h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            Upload meerdere facturen tegelijk. De AI analyseert ze parallel voor een razendsnel resultaat.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Input Section */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200 sticky top-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Facturen Toevoegen
              </h2>

              <div className="space-y-6">
                {/* File Upload */}
                <div>
                  <div 
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    className={`relative border-2 border-dashed rounded-2xl p-6 text-center transition-colors ${
                      isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'
                    }`}
                  >
                    <input
                      type="file"
                      multiple
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept="image/*,application/pdf"
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <div className="flex flex-col items-center justify-center space-y-2 pointer-events-none">
                      <Upload className={`w-8 h-8 ${isDragging ? 'text-blue-500' : 'text-slate-400'}`} />
                      <span className="text-sm font-medium text-slate-600">Klik of sleep bestanden hierheen</span>
                      <span className="text-xs text-slate-400">Meerdere PDF's of afbeeldingen</span>
                    </div>
                  </div>
                </div>

                <div className="relative flex items-center py-2">
                  <div className="flex-grow border-t border-slate-200"></div>
                  <span className="flex-shrink-0 mx-4 text-slate-400 text-sm font-medium uppercase">Of</span>
                  <div className="flex-grow border-t border-slate-200"></div>
                </div>

                {/* Text Input */}
                <div>
                  <textarea
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Plak hier de inhoud van een factuur..."
                    className="w-full h-24 rounded-2xl border border-slate-300 p-4 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow resize-none mb-2"
                  />
                  <button
                    onClick={handleAddTextInvoice}
                    disabled={!textInput.trim()}
                    className="w-full py-2 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-medium text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Voeg tekst toe als factuur
                  </button>
                </div>

                <hr className="border-slate-100" />

                {/* Global Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                    <Settings2 className="w-4 h-4 text-slate-500" />
                    Batch Instellingen
                  </h3>
                  
                  {/* Invoice Type Selector */}
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">
                      Type Factuur
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['Automatisch', 'Aankoop', 'Verkoop'] as InvoiceTypeOption[]).map((type) => (
                        <button
                          key={type}
                          onClick={() => setGlobalInvoiceType(type)}
                          className={`py-2 px-3 rounded-xl text-sm font-medium transition-colors border ${
                            globalInvoiceType === type 
                              ? 'bg-blue-50 border-blue-200 text-blue-700' 
                              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Global Deduction Percentage */}
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider flex items-center gap-1">
                      Aftrekpercentage (Aankopen)
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={globalDeduction}
                        onChange={(e) => setGlobalDeduction(Number(e.target.value))}
                        className="flex-grow h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                      />
                      <div className="w-16 px-3 py-2 bg-slate-100 rounded-xl text-center font-semibold text-slate-700 border border-slate-200">
                        {globalDeduction}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  onClick={handleAnalyzeAll}
                  disabled={isAnalyzingAny || pendingCount === 0}
                  className="w-full py-4 px-6 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-semibold text-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-sm hover:shadow-md active:scale-[0.98]"
                >
                  {isAnalyzingAny ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Bezig met analyseren...
                    </>
                  ) : (
                    <>
                      <Calculator className="w-5 h-5" />
                      Analyseer {pendingCount > 0 ? `${pendingCount} factu${pendingCount === 1 ? 'ur' : 'ren'}` : 'Alles'}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Results Section */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* Summary Table */}
            {hasSummary && (
              <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-slate-900">
                  <Table className="w-5 h-5 text-blue-600" />
                  Samenvatting Btw-aangifte
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {Object.entries(summary).sort(([a], [b]) => a.localeCompare(b)).map(([code, total]) => (
                    <div key={code} className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex flex-col items-center justify-center text-center">
                      <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm mb-2">
                        {code}
                      </div>
                      <span className="text-sm font-semibold text-slate-900">{formatCurrency(total)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Invoices List */}
            <div className="space-y-4">
              {invoices.length === 0 ? (
              <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-center p-8 bg-slate-100/50 rounded-3xl border border-slate-200 border-dashed">
                <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-sm mb-6">
                  <Receipt className="w-10 h-10 text-slate-300" />
                </div>
                <h3 className="text-xl font-semibold text-slate-700 mb-2">Geen facturen toegevoegd</h3>
                <p className="text-slate-500 max-w-sm">
                  Upload documenten of plak tekst aan de linkerkant om te beginnen met de batch-analyse.
                </p>
              </div>
            ) : (
              invoices.map((inv, index) => (
                <div key={inv.id} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-all">
                  {/* Header */}
                  <div 
                    className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors"
                    onClick={() => toggleExpand(inv.id)}
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="flex-shrink-0">
                        {inv.status === 'idle' && <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center"><FileText className="w-4 h-4 text-slate-400" /></div>}
                        {inv.status === 'analyzing' && <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center"><Loader2 className="w-4 h-4 text-blue-600 animate-spin" /></div>}
                        {inv.status === 'success' && <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center"><CheckCircle2 className="w-4 h-4 text-green-600" /></div>}
                        {inv.status === 'error' && <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center"><AlertCircle className="w-4 h-4 text-red-600" /></div>}
                      </div>
                      <div className="truncate">
                        <h3 className="text-sm font-semibold text-slate-900 truncate">
                          {inv.file ? inv.file.name : `Tekstfactuur #${index + 1}`}
                        </h3>
                        <p className="text-xs text-slate-500">
                          {inv.status === 'idle' && 'Klaar voor analyse'}
                          {inv.status === 'analyzing' && 'Analyseren...'}
                          {inv.status === 'success' && `${inv.result?.document_info?.leverancier_of_klant || 'Onbekend'} • ${inv.result?.document_info?.datum || 'Onbekend'}`}
                          {inv.status === 'error' && <span className="text-red-500">Fout opgetreden</span>}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                      {inv.status === 'success' && inv.result?.compliance_en_waarschuwingen && !inv.result.compliance_en_waarschuwingen.is_factuur_wettelijk_geldig && (
                        <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center" title="Factuur is niet wettelijk geldig">
                          <FileWarning className="w-3 h-3 text-red-600" />
                        </div>
                      )}
                      <button 
                        onClick={(e) => { e.stopPropagation(); removeInvoice(inv.id); }}
                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="Verwijder"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <div className="p-2 text-slate-400">
                        {inv.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {inv.expanded && (
                    <div className="border-t border-slate-100 bg-slate-50/50 p-4 md:p-6">
                      {inv.status === 'error' && (
                        <div className="p-4 bg-red-50 text-red-700 rounded-xl flex items-start gap-3 border border-red-100">
                          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                          <p className="text-sm">{inv.error}</p>
                        </div>
                      )}

                      {inv.status === 'success' && inv.result && (
                        <div className="animate-in fade-in duration-300">
                          
                          {/* Compliance Warnings */}
                          {inv.result.compliance_en_waarschuwingen && (
                            <div className="mb-6 space-y-3">
                              {!inv.result.compliance_en_waarschuwingen.is_factuur_wettelijk_geldig && (
                                <div className="p-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
                                  <FileWarning className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                                  <div>
                                    <h4 className="text-sm font-semibold text-red-900">Factuur is niet wettelijk geldig</h4>
                                    <p className="text-xs text-red-700 mt-1">Ontbrekende velden: {inv.result.compliance_en_waarschuwingen.ontbrekende_verplichte_velden.join(', ')}</p>
                                  </div>
                                </div>
                              )}
                              {inv.result.compliance_en_waarschuwingen.fiscale_waarschuwing_aftrekbaarheid && inv.result.compliance_en_waarschuwingen.fiscale_waarschuwing_aftrekbaarheid !== "Geen opmerkingen. Percentage lijkt logisch voor dit type aankoop." && (
                                <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl flex items-start gap-3">
                                  <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                                  <div>
                                    <h4 className="text-sm font-semibold text-amber-900">Fiscale Waarschuwing</h4>
                                    <p className="text-xs text-amber-800 mt-1">{inv.result.compliance_en_waarschuwingen.fiscale_waarschuwing_aftrekbaarheid}</p>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Advanced Rules Badges */}
                          {inv.result.geavanceerde_regels && (inv.result.geavanceerde_regels.is_medecontractant_of_btw_verlegd || inv.result.geavanceerde_regels.is_intracommunautaire_verwerving) && (
                            <div className="flex flex-wrap gap-2 mb-6">
                              {inv.result.geavanceerde_regels.is_medecontractant_of_btw_verlegd && (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-100 text-purple-800 text-xs font-semibold border border-purple-200">
                                  <AlertCircle className="w-3 h-3" />
                                  Btw Verlegd (Medecontractant)
                                </span>
                              )}
                              {inv.result.geavanceerde_regels.is_intracommunautaire_verwerving && (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-100 text-indigo-800 text-xs font-semibold border border-indigo-200">
                                  <Globe className="w-3 h-3" />
                                  Intracommunautaire Verwerving (EU)
                                </span>
                              )}
                            </div>
                          )}

                          {/* Calculations Summary */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                            <div className="p-3 rounded-xl bg-white border border-slate-200">
                              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Totaal Excl.</p>
                              <p className="text-base font-semibold text-slate-900">{formatCurrency(inv.result.berekeningen?.totaal_excl_btw)}</p>
                            </div>
                            <div className="p-3 rounded-xl bg-white border border-slate-200">
                              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Totaal Btw</p>
                              <p className="text-base font-semibold text-slate-900">{formatCurrency(inv.result.berekeningen?.totaal_btw)}</p>
                            </div>
                            <div className="p-3 rounded-xl bg-blue-50 border border-blue-100">
                              <p className="text-[10px] font-bold text-blue-600 uppercase tracking-wider mb-1">Aftrekbaar</p>
                              <p className="text-base font-semibold text-blue-900">{formatCurrency(inv.result.berekeningen?.aftrekbare_btw)}</p>
                            </div>
                            <div className="p-3 rounded-xl bg-orange-50 border border-orange-100">
                              <p className="text-[10px] font-bold text-orange-600 uppercase tracking-wider mb-1">Verworpen</p>
                              <p className="text-base font-semibold text-orange-900">{formatCurrency(inv.result.berekeningen?.niet_aftrekbare_btw)}</p>
                            </div>
                          </div>

                          {/* Roosters */}
                          <div className="bg-white p-4 rounded-xl border border-slate-200 mb-6">
                            {renderRoosterSection("Uitgaande Handelingen", inv.result.btw_aangifte_roosters?.uitgaande_handelingen_basis)}
                            {renderRoosterSection("Inkomende Handelingen", inv.result.btw_aangifte_roosters?.inkomende_handelingen_basis)}
                            {renderRoosterSection("Verschuldigde Btw", inv.result.btw_aangifte_roosters?.verschuldigde_belasting)}
                            {renderRoosterSection("Aftrekbare Btw", inv.result.btw_aangifte_roosters?.aftrekbare_belasting)}
                            
                            {(!inv.result.btw_aangifte_roosters || 
                              (Object.values(inv.result.btw_aangifte_roosters.uitgaande_handelingen_basis || {}).every(v => !v) &&
                               Object.values(inv.result.btw_aangifte_roosters.inkomende_handelingen_basis || {}).every(v => !v) &&
                               Object.values(inv.result.btw_aangifte_roosters.verschuldigde_belasting || {}).every(v => !v) &&
                               Object.values(inv.result.btw_aangifte_roosters.aftrekbare_belasting || {}).every(v => !v))) && (
                              <div className="text-center text-sm text-slate-500 py-2">
                                Geen roosters van toepassing gevonden.
                              </div>
                            )}
                          </div>

                          {/* AI Explanation */}
                          {inv.result.ai_verantwoording && (
                            <div className="p-4 rounded-xl bg-slate-800 text-slate-200">
                              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <AlertCircle className="w-3 h-3" />
                                Verantwoording
                              </h4>
                              <p className="text-xs leading-relaxed">{inv.result.ai_verantwoording}</p>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {inv.status === 'idle' && (
                        <div className="text-sm text-slate-500 text-center py-4">
                          Klaar om geanalyseerd te worden. Klik op "Analyseer Alles".
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

