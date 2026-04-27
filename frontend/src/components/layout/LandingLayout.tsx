import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, ChevronDown, Lock, Zap, EyeOff, ArrowUpRight } from "lucide-react";
import { useState } from "react";

interface LandingLayoutProps {
  onUpload: () => void;
}

// Reusable floating stat card
function FloatCard({
  value, label, accent, bg, delay, rotateZ, animY,
}: {
  value: string; label: string; accent: string; bg: string;
  delay: number; rotateZ: string; animY: [number, number, number];
}) {
  return (
    <motion.div
      animate={{ y: animY }}
      transition={{ repeat: Infinity, duration: 4.5 + delay, ease: "easeInOut", delay }}
      style={{ rotate: rotateZ, background: bg, boxShadow: `0 12px 36px ${accent}22` }}
      className="rounded-[20px] px-7 py-6 min-w-[172px] cursor-default select-none"
      whileHover={{ scale: 1.04, rotate: '0deg' }}
    >
      <div className="flex items-start justify-between mb-1">
        <span className="text-[40px] font-[800] tabular-nums leading-none text-[#0F0F1A]">{value}</span>
        <ArrowUpRight className="w-4 h-4 mt-2 opacity-40" style={{ color: accent }} />
      </div>
      <div className="w-10 h-[2.5px] rounded-full my-2.5" style={{ background: accent }} />
      <span className="text-[12px] font-semibold text-[#6B7280]">{label}</span>
    </motion.div>
  );
}

export default function LandingLayout({ onUpload }: LandingLayoutProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);

  return (
    <div className="min-h-screen font-sans overflow-hidden relative flex flex-col"
      style={{ background: '#F7F4EF' }}>

      {/* ── Ambient background glows ── */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[30%] w-[700px] h-[700px] rounded-full opacity-40"
          style={{ background: 'radial-gradient(circle, rgba(108,71,255,0.07) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-5%] right-[25%] w-[600px] h-[600px] rounded-full opacity-30"
          style={{ background: 'radial-gradient(circle, rgba(255,107,53,0.07) 0%, transparent 70%)' }} />
        {/* Dot grid */}
        <div className="absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage: 'radial-gradient(circle, #C4BAF0 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }} />
      </div>

      {/* ── Nav ── */}
      <nav className="relative z-20 flex items-center justify-between px-8 lg:px-16 py-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6C47FF, #4F35CC)' }}>
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="text-[15px] font-[800] tracking-tight text-[#0F0F1A]">DataLens</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-[13px] font-medium text-[#6B7280]">
          <a href="#" className="hover:text-[#0F0F1A] transition-colors">How it works</a>
          <a href="#" className="hover:text-[#0F0F1A] transition-colors">Features</a>
          <a href="#" className="hover:text-[#0F0F1A] transition-colors">Security</a>
        </div>
        <button
          onClick={onUpload}
          className="hidden md:flex items-center gap-2 text-[13px] font-semibold text-white px-5 py-2.5 rounded-[10px] transition-all hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, #6C47FF, #4F35CC)', boxShadow: '0 4px 14px rgba(108,71,255,0.35)' }}>
          Try free <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </nav>

      {/* ── Hero Grid ── */}
      <div className="flex-1 flex items-center">
        <div className="w-full max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,600px)_1fr] gap-6 px-6 lg:px-12 py-8 relative z-10">

          {/* Left cards */}
          <div className="hidden lg:flex flex-col items-end justify-center gap-8 pr-4">
            <FloatCard
              value="2.4M" label="Rows processed"
              accent="#6C47FF" bg="#EDE8FF"
              delay={0} rotateZ="-2.5deg" animY={[0, -12, 0]}
            />
            <FloatCard
              value="< 60s" label="Avg analysis time"
              accent="#00C896" bg="#D6F7EE"
              delay={0.7} rotateZ="2deg" animY={[0, 9, 0]}
            />
          </div>

          {/* Center */}
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="flex flex-col items-center"
          >
            {/* Headline */}
            <div className="text-center mb-10">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-6 text-[11px] font-semibold uppercase tracking-widest"
                style={{ background: 'rgba(108,71,255,0.08)', color: '#6C47FF', border: '1px solid rgba(108,71,255,0.2)' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-[#6C47FF] animate-pulse inline-block" />
                Powered by Claude AI
              </div>
              <h1 className="font-[800] text-[64px] md:text-[76px] leading-[1.08] tracking-[-0.03em] text-[#0F0F1A] mb-5">
                Drop your CSV.<br />
                <span style={{
                  background: 'linear-gradient(135deg, #6C47FF 0%, #A855F7 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}>
                  Get AI insights.
                </span>
              </h1>
              <p className="text-[16px] text-[#6B7280] max-w-[420px] mx-auto leading-relaxed">
                Upload any CSV and Claude builds a full dashboard — charts, findings, and chat — in under 60 seconds.
              </p>
            </div>

            {/* Dropzone */}
            <motion.div
              whileHover={{ scale: 1.015 }}
              whileTap={{ scale: 0.985 }}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => { e.preventDefault(); setIsDragging(false); onUpload(); }}
              onClick={onUpload}
              className="w-full cursor-pointer relative rounded-[24px] p-10 flex flex-col items-center transition-all duration-300"
              style={{
                background: isDragging ? 'rgba(108,71,255,0.04)' : '#FFFFFF',
                border: isDragging ? '2px dashed #6C47FF' : '2px dashed #D4CEFC',
                boxShadow: isDragging
                  ? '0 0 0 4px rgba(108,71,255,0.1), 0 20px 48px rgba(0,0,0,0.06)'
                  : '0 8px 40px rgba(0,0,0,0.05)',
              }}
            >
              {/* Upload icon with glow */}
              <div className="relative mb-5">
                <div className="absolute inset-0 rounded-full blur-xl opacity-30"
                  style={{ background: '#6C47FF', transform: 'scale(1.5)' }} />
                <div className="relative w-16 h-16 rounded-2xl flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, rgba(108,71,255,0.12), rgba(108,71,255,0.06))' }}>
                  <UploadCloud className="w-8 h-8" style={{ color: '#6C47FF' }} />
                </div>
              </div>

              <h3 className="text-[20px] font-[700] text-[#0F0F1A] mb-1.5">
                Drop your CSV file here
              </h3>
              <p className="text-[14px] text-[#9CA3AF] mb-7">or click anywhere to browse</p>

              <button
                className="flex items-center gap-2 text-[14px] font-[700] text-white px-8 py-3.5 rounded-[14px] transition-all hover:opacity-90 hover:scale-[1.02] active:scale-[0.98] mb-5"
                style={{
                  background: 'linear-gradient(135deg, #6C47FF 0%, #4F35CC 100%)',
                  boxShadow: '0 8px 24px rgba(108,71,255,0.4)',
                }}>
                Analyse now <span className="text-white/70">→</span>
              </button>

              <p className="text-[11px] font-semibold text-[#C4BAF0] uppercase tracking-widest">
                .csv only · max 50MB
              </p>
            </motion.div>

            {/* Trust bar */}
            <div className="mt-6 flex flex-col items-center gap-3 w-full">
              <div className="flex items-center gap-5 px-6 py-3 rounded-full"
                style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid #E5E0D8', backdropFilter: 'blur(8px)' }}>
                {[
                  { icon: Lock, label: 'Files never stored' },
                  { icon: Zap, label: 'Memory only' },
                  { icon: EyeOff, label: 'Not shared' },
                ].map(({ icon: Icon, label }, i) => (
                  <div key={label} className="flex items-center gap-1.5">
                    {i > 0 && <div className="w-px h-3 bg-[#E5E0D8] mx-1" />}
                    <Icon className="w-3.5 h-3.5 text-[#9CA3AF]" />
                    <span className="text-[11px] font-medium text-[#6B7280]">{label}</span>
                  </div>
                ))}
              </div>

              {/* Expandable privacy */}
              <button
                onClick={() => setShowPrivacy(!showPrivacy)}
                className="flex items-center gap-1 text-[11px] text-[#9CA3AF] hover:text-[#6C47FF] transition-colors font-medium"
              >
                How your data is handled
                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${showPrivacy ? 'rotate-180' : ''}`} />
              </button>
              <AnimatePresence>
                {showPrivacy && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden w-full max-w-md"
                  >
                    <div className="p-4 rounded-[14px] text-[11px] leading-[1.8] text-[#6B7280]"
                      style={{ background: 'rgba(255,255,255,0.8)', border: '1px solid #E5E0D8' }}>
                      Your file is sent to Claude AI for analysis only. It is never written to a database,
                      stored on any server, or retained after your session ends. Each upload is isolated —
                      no data is shared between users or sessions. We do not collect your name, email, or
                      any personal information.
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>

          {/* Right cards */}
          <div className="hidden lg:flex flex-col items-start justify-center gap-8 pl-4">
            <FloatCard
              value="47" label="Insights generated"
              accent="#FF6B35" bg="#FFE8DF"
              delay={1} rotateZ="2.5deg" animY={[0, 11, 0]}
            />
            <FloatCard
              value="100%" label="AI-powered charts"
              accent="#FFB800" bg="#FFF3CC"
              delay={1.4} rotateZ="-2deg" animY={[0, -8, 0]}
            />
          </div>

        </div>
      </div>
    </div>
  );
}
