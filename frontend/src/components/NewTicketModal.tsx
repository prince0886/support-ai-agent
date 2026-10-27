import { createContext, useContext, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import { api, errorMessage } from "../lib/api";
import { useApp } from "../store/AppStore";
import { Spinner } from "./ui";
import { useNavigate } from "react-router-dom";
import { Sparkles, X } from "lucide-react";

interface Sample {
  label: string;
  name: string;
  email: string;
  subject: string;
  channel: "email" | "chat";
  message: string;
}

const SAMPLES: Sample[] = [
  {
    label: "Delayed shipment",
    name: "Maya Chen",
    email: "maya.chen@example.com",
    subject: "Order NW-48213 still hasn't shipped",
    channel: "email",
    message:
      "Hi, I ordered a camping stove six days ago with standard shipping and tracking has been stuck on 'label created' since Tuesday. We leave for a trip on Friday and I really need it before then. Can you check what's happening with order NW-48213?",
  },
  {
    label: "Refund request",
    name: "Daniel Okafor",
    email: "daniel.okafor@example.com",
    subject: "Refund for unopened Ridgeline 4P tent",
    channel: "email",
    message:
      "I bought the Ridgeline 4P tent last week (order NW-47118) but we ended up using a friend's tent. It's still sealed in the original box. Can I return it for a refund? Happy to ship it back.",
  },
  {
    label: "Failed payment",
    name: "Priya Raman",
    email: "priya.raman@example.com",
    subject: "Payment declined but money is missing from my account",
    channel: "chat",
    message:
      "I tried to renew my subscription today. The checkout said my card was declined, but my bank app shows a pending charge of $89 from Northwind. I do not want to be charged twice and I need this cleared up today.",
  },
  {
    label: "Technical issue",
    name: "Tom Becker",
    email: "tom.becker@example.com",
    subject: "Dashboard stuck on ERR-500 after update",
    channel: "chat",
    message:
      "Since your latest update the dashboard just spins and then shows 'Something went wrong (ERR-500)'. I've tried Chrome, Edge and the mobile app, and cleared the cache twice. I manage 12 team accounts and we're completely blocked. This is urgent.",
  },
  {
    label: "Policy exception",
    name: "Angela Torres",
    email: "angela.torres@example.com",
    subject: "Refusing my refund over 9 days is unacceptable",
    channel: "email",
    message:
      "I've been a customer for four years and you're seriously refusing to refund a $340 jacket because I'm 9 days past your 30-day window? The jacket is unworn with tags. This is ridiculous. Make an exception or I'm disputing the charge with my bank and posting about this everywhere.",
  },
];

interface NewTicketContextValue {
  open: () => void;
}

const NewTicketContext = createContext<NewTicketContextValue | null>(null);

export function NewTicketProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <NewTicketContext.Provider value={{ open: () => setIsOpen(true) }}>
      {children}
      <NewTicketModal open={isOpen} onClose={() => setIsOpen(false)} />
    </NewTicketContext.Provider>
  );
}

export function useNewTicket(): NewTicketContextValue {
  const context = useContext(NewTicketContext);
  if (!context) throw new Error("useNewTicket must be used inside NewTicketProvider");
  return context;
}

function NewTicketModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { status, refresh, toast } = useApp();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [channel, setChannel] = useState<"email" | "chat">("email");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const messageRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => messageRef.current?.focus(), 60);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose, submitting]);

  if (!open) return null;

  const applySample = (sample: Sample) => {
    setName(sample.name);
    setEmail(sample.email);
    setSubject(sample.subject);
    setChannel(sample.channel);
    setMessage(sample.message);
    messageRef.current?.focus();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (message.trim().length < 3) {
      toast("Add a customer message before analyzing.", "error");
      return;
    }
    setSubmitting(true);
    try {
      const ticket = await api.createTicket({
        message: message.trim(),
        customer_name: name.trim() || undefined,
        customer_email: email.trim() || undefined,
        subject: subject.trim() || undefined,
        channel,
      });
      await refresh();
      toast(`${ticket.reference} analyzed and added to the inbox.`, "success");
      setName("");
      setEmail("");
      setSubject("");
      setMessage("");
      setChannel("email");
      onClose();
      navigate(`/inbox/${ticket.id}`);
    } catch (cause) {
      toast(errorMessage(cause), "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/40 p-4 backdrop-blur-sm sm:p-8">
      <div className="animate-fade-in my-auto w-full max-w-2xl rounded-2xl bg-white shadow-raised">
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">New customer query</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              SupportPilot classifies, retrieves knowledge and drafts a reply before a human approves it.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm -mr-2"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={submit} className="px-6 py-5">
          <div className="mb-4">
            <span className="label">Load a demo scenario</span>
            <div className="flex flex-wrap gap-1.5">
              {SAMPLES.map((sample) => (
                <button
                  key={sample.label}
                  type="button"
                  onClick={() => applySample(sample)}
                  className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="customer-name">
                Customer name
              </label>
              <input
                id="customer-name"
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Maya Chen"
              />
            </div>
            <div>
              <label className="label" htmlFor="customer-email">
                Email
              </label>
              <input
                id="customer-email"
                type="email"
                className="input"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="maya@example.com"
              />
            </div>
            <div>
              <label className="label" htmlFor="ticket-subject">
                Subject <span className="font-normal text-slate-400">(optional)</span>
              </label>
              <input
                id="ticket-subject"
                className="input"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                placeholder="Derived from the message if left empty"
              />
            </div>
            <div>
              <label className="label" htmlFor="ticket-channel">
                Channel
              </label>
              <select
                id="ticket-channel"
                className="input"
                value={channel}
                onChange={(event) => setChannel(event.target.value as "email" | "chat")}
              >
                <option value="email">Email</option>
                <option value="chat">Live chat</option>
              </select>
            </div>
          </div>

          <div className="mt-4">
            <label className="label" htmlFor="ticket-message">
              Customer message
            </label>
            <textarea
              id="ticket-message"
              ref={messageRef}
              className="input min-h-[132px] resize-y"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Paste the customer's message here…"
            />
            <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-slate-400">
              <Sparkles className="h-3 w-3" />
              {status?.ai.mode === "llm"
                ? `Analysis runs through ${status.ai.provider} (${status.ai.model}).`
                : "No live model configured: the built-in deterministic analyst will classify and draft."}
            </p>
          </div>

          <div className="mt-5 flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
            <p className="text-[11px] text-slate-400">
              Drafts are never sent automatically. A human approves every reply.
            </p>
            <div className="flex items-center gap-2">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? (
                  <>
                    <Spinner /> Analyzing…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" /> Analyze & create ticket
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}